// Localhost TCP bridge, the Unity copy of bridge/godot/bridge.gd. One JSON object per line each way.
// Request:  {"id": 1, "cmd": "get_state", "args": {...}}
// Response: {"id": 1, "ok": true, "result": {...}} or {"id": 1, "ok": false, "error": "..."}
// Socket threads only queue lines. Every command runs on the main thread.
//
// Each feature registers its own commands and get_state keys (Register, RegisterAsync, AddState).
// So a feature (or a parallel agent) adds commands from its own asmdef
// and never edits this file.
using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

namespace GameBridge
{
	[DefaultExecutionOrder(-1000)]
	public sealed class BridgeServer : MonoBehaviour
	{
		public delegate object Handler(Dictionary<string, object> args);
		// An async handler runs as a coroutine and calls done(result) once.
		public delegate IEnumerator AsyncHandler(Dictionary<string, object> args, Action<object> done);

		public static BridgeServer Instance { get; private set; }

		[RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
		static void ResetStatics() { Instance = null; }

		readonly Dictionary<string, AsyncHandler> _commands = new Dictionary<string, AsyncHandler>();
		readonly List<Action<Dictionary<string, object>>> _state = new List<Action<Dictionary<string, object>>>();
		readonly ConcurrentQueue<(TcpClient client, string line)> _inbox = new ConcurrentQueue<(TcpClient, string)>();
		TcpListener _listener;
		Thread _acceptThread;

		public int Port { get; private set; }
		public bool Listening { get; private set; }
		// Real time of the last command: the idle quit reads it.
		public float LastCommandRealtime { get; private set; }
		public IEnumerable<string> Commands => _commands.Keys;

		void Awake()
		{
			if (Instance != null && Instance != this) { Destroy(this); return; }
			Instance = this;
			LastCommandRealtime = Time.realtimeSinceStartup;
		}

		void OnDestroy()
		{
			if (Instance == this) Instance = null;
			Stop();
		}

		void OnApplicationQuit() { Stop(); }

		public void Listen(int port)
		{
			Port = port;
			_listener = new TcpListener(IPAddress.Loopback, port);
			try { _listener.Start(); }
			catch (Exception e)
			{
				Debug.LogError($"bridge: cannot listen on 127.0.0.1:{port} ({e.Message})");
				_listener = null;
				return;
			}
			_acceptThread = new Thread(AcceptLoop) { IsBackground = true, Name = "bridge-accept" };
			_acceptThread.Start();
			Listening = true;
			Debug.Log($"BRIDGE_READY 127.0.0.1:{port}");
		}

		public void Stop()
		{
			Listening = false;
			try { if (_listener != null) _listener.Stop(); } catch (Exception) { }
			_listener = null;
		}

		public void Register(string cmd, Handler handler) => _commands[cmd] = (a, done) => Sync(handler, a, done);

		public void RegisterAsync(string cmd, AsyncHandler handler) => _commands[cmd] = handler;

		// fill(state) adds this feature's keys to every get_state reply.
		public void AddState(Action<Dictionary<string, object>> fill) => _state.Add(fill);

		public bool Has(string cmd) => _commands.ContainsKey(cmd);

		public Dictionary<string, object> State()
		{
			var s = new Dictionary<string, object>();
			foreach (var fill in _state) fill(s);
			return s;
		}

		static IEnumerator Sync(Handler h, Dictionary<string, object> a, Action<object> done)
		{
			done(h(a));
			yield break;
		}

		void AcceptLoop()
		{
			try
			{
				while (true)
				{
					var listener = _listener;
					if (listener == null) return;
					var c = listener.AcceptTcpClient();
					c.NoDelay = true;
					new Thread(() => ReadLoop(c)) { IsBackground = true, Name = "bridge-client" }.Start();
				}
			}
			catch (Exception) { /* the listener stopped at quit */ }
		}

		void ReadLoop(TcpClient c)
		{
			try
			{
				var r = new StreamReader(c.GetStream(), new UTF8Encoding(false));
				string line;
				while ((line = r.ReadLine()) != null)
					if (line.Trim().Length > 0) _inbox.Enqueue((c, line));
			}
			catch (Exception) { }
		}

		// Commands also run at the top of each game tick (execution order -1000, before game FixedUpdates), so a
		// get_state or a reply never waits behind the catch-up ticks of a slow frame.
		void FixedUpdate() { Drain(); }

		void Update() { Drain(); }

		void Drain()
		{
			while (_inbox.TryDequeue(out var m))
			{
				LastCommandRealtime = Time.realtimeSinceStartup;
				StartCoroutine(Handle(m.client, m.line));
			}
		}

		IEnumerator Handle(TcpClient c, string line)
		{
			Dictionary<string, object> msg = null;
			try { msg = MiniJson.Parse(line) as Dictionary<string, object>; } catch (Exception) { }
			if (msg == null)
			{
				Send(c, new Dictionary<string, object> { { "id", null }, { "ok", false }, { "error", "bad json" } });
				yield break;
			}
			msg.TryGetValue("id", out var id);
			string cmd = msg.TryGetValue("cmd", out var cv) ? Convert.ToString(cv) : "";
			var args = msg.TryGetValue("args", out var av) && av is Dictionary<string, object> ad ? ad : new Dictionary<string, object>();
			object result = null;
			bool finished = false;
			if (_commands.TryGetValue(cmd, out var handler))
			{
				IEnumerator run = null;
				try { run = handler(args, r => { result = r; finished = true; }); }
				catch (Exception e) { result = Json.Error($"{cmd} failed: {e.Message}"); finished = true; Debug.LogException(e); }
				if (run != null) yield return Guard(run, cmd, e => { result = Json.Error($"{cmd} failed: {e.Message}"); finished = true; });
				if (!finished) result = Json.Error($"{cmd} gave no result");
			}
			else
			{
				result = Json.Error($"unknown command '{cmd}'");
			}
			if (result is Dictionary<string, object> d && d.TryGetValue("error", out var err))
				Send(c, new Dictionary<string, object> { { "id", id }, { "ok", false }, { "error", Convert.ToString(err) } });
			else
				Send(c, new Dictionary<string, object> { { "id", id }, { "ok", true }, { "result", result } });
		}

		// Runs a handler coroutine and turns an exception into an error reply (a coroutine cannot try/catch a yield).
		static IEnumerator Guard(IEnumerator run, string cmd, Action<Exception> fail)
		{
			while (true)
			{
				object cur;
				try
				{
					if (!run.MoveNext()) yield break;
					cur = run.Current;
				}
				catch (Exception e)
				{
					Debug.LogException(e);
					fail(e);
					yield break;
				}
				yield return cur;
			}
		}

		static void Send(TcpClient c, object obj)
		{
			try
			{
				var b = Encoding.UTF8.GetBytes(MiniJson.Write(obj) + "\n");
				lock (c) c.GetStream().Write(b, 0, b.Length);
			}
			catch (Exception) { }
		}
	}
}
