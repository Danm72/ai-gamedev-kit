// Helpers for bridge handlers: read typed args, round numbers as Godot's snappedf does, build replies.
using System;
using System.Collections.Generic;
using UnityEngine;

namespace GameBridge
{
	public static class Json
	{
		// A reply with this key goes out as {"ok": false, "error": ...}, as in the Godot bridge.
		public static Dictionary<string, object> Error(string message) =>
			new Dictionary<string, object> { { "error", message } };

		// snappedf(x, step). The outer round drops float noise (92 x 0.1 = 9.200000000000001) from the JSON.
		public static double R(double x, double step = 0.01) => Math.Round(Math.Round(x / step) * step, 6);

		public static List<object> V(Vector3 p, double step = 0.01) => new List<object> { R(p.x, step), R(p.y, step), R(p.z, step) };

		public static double Num(Dictionary<string, object> a, string key, double fallback)
		{
			if (a == null || !a.TryGetValue(key, out var v) || v == null) return fallback;
			switch (v)
			{
				case double d: return d;
				case bool b: return b ? 1 : 0;
				case string s: return double.TryParse(s, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var p) ? p : fallback;
				default: return fallback;
			}
		}

		public static string Str(Dictionary<string, object> a, string key, string fallback = "") =>
			a != null && a.TryGetValue(key, out var v) && v != null ? Convert.ToString(v, System.Globalization.CultureInfo.InvariantCulture) : fallback;

		public static bool Bool(Dictionary<string, object> a, string key, bool fallback)
		{
			if (a == null || !a.TryGetValue(key, out var v) || v == null) return fallback;
			return ToBool(v);
		}

		// Godot's bool(value): numbers are true when not 0, strings when not empty.
		public static bool ToBool(object v)
		{
			switch (v)
			{
				case bool b: return b;
				case double d: return d != 0;
				case string s: return s.Length > 0 && s != "false" && s != "0";
				default: return v != null;
			}
		}

		public static double ToNum(object v, double fallback = 0)
		{
			switch (v)
			{
				case double d: return d;
				case bool b: return b ? 1 : 0;
				case string s: return double.TryParse(s, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var p) ? p : fallback;
				default: return fallback;
			}
		}

		// [x, y, z] from the bridge (3 numbers).
		public static Vector3 Vec(List<object> l) => new Vector3((float)ToNum(l[0]), (float)ToNum(l[1]), (float)ToNum(l[2]));
	}
}
