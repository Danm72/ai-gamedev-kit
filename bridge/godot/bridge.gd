class_name Bridge
extends Node
## Localhost TCP bridge. One JSON object per line in each direction.
## Request:  {"id": 1, "cmd": "get_state", "args": {...}}
## Response: {"id": 1, "ok": true, "result": {...}} or {"id": 1, "ok": false, "error": "..."}

## Usage (in your main scene):
##   var bridge := Bridge.new()
##   bridge.handler = self   # self has run_command(); it may `await` and return a Dictionary
##   add_child(bridge)
##   bridge.start(9177)
## A handler result with an "error" key goes out as {"ok": false, "error": ...}.

var handler: Node   # any node with `func run_command(cmd: String, args: Dictionary) -> Variant`
var port := 9177
var _server := TCPServer.new()
var _clients: Array = []     # [{peer: StreamPeerTCP, buf: PackedByteArray}]
## Idle quit: an agent's game with no bridge command and no player input for idle_quit_s quits,
## so a forgotten window does not hold memory or a slot. Off for the ports in human_ports (the
## games you play yourself), for movie renders and SceneTree drivers (-s), and when
## BRIDGE_IDLE_QUIT_S=0 (a launcher that needs a long quiet game sets it; any number is seconds).
var idle_quit_s := 60.0
var human_ports: Array[int] = [9177]
## Called on idle quit. Point it at your own clean-quit function if you have one (audio fade, saves).
var quit_func := func() -> void: get_tree().quit()
var _last_activity_ms := 0
var _first_frame := true   # the clock restarts on the first frame, so a slow scene load never counts
var _busy := 0   # commands still running (sim_input and step can await for many seconds)


func start(p: int) -> void:
	port = p
	var err := _server.listen(port, "127.0.0.1")
	if err != OK:
		push_error("bridge: cannot listen on %d (%d)" % [port, err])
	else:
		print("BRIDGE_READY 127.0.0.1:%d" % port)
	var env := OS.get_environment("BRIDGE_IDLE_QUIT_S")
	if env != "":
		idle_quit_s = float(env)
	if port in human_ports or Engine.get_write_movie_path() != "" or get_tree().get_script() != null:
		idle_quit_s = 0.0
	_last_activity_ms = Time.get_ticks_msec()


func _input(_event: InputEvent) -> void:
	_last_activity_ms = Time.get_ticks_msec()


func _process(_delta: float) -> void:
	while _server.is_connection_available():
		var peer := _server.take_connection()
		peer.set_no_delay(true)
		_clients.append({"peer": peer, "buf": PackedByteArray()})
	for c in _clients.duplicate():
		var peer: StreamPeerTCP = c.peer
		peer.poll()
		var st := peer.get_status()
		if st != StreamPeerTCP.STATUS_CONNECTED:
			_clients.erase(c)
			continue
		var n := peer.get_available_bytes()
		if n > 0:
			var res := peer.get_data(n)
			if res[0] == OK:
				c.buf.append_array(res[1])
		while true:
			var idx: int = c.buf.find(10)
			if idx < 0:
				break
			var line: String = c.buf.slice(0, idx).get_string_from_utf8()
			c.buf = c.buf.slice(idx + 1)
			if line.strip_edges() != "":
				_handle(peer, line)
	# After the sockets are read, so a command that waited out a slow frame still counts.
	if _first_frame or _busy > 0 or Input.is_anything_pressed():
		_first_frame = false
		_last_activity_ms = Time.get_ticks_msec()
	elif idle_quit_s > 0.0 and Time.get_ticks_msec() - _last_activity_ms > int(idle_quit_s * 1000.0):
		print("IDLE_QUIT: no bridge command or input for %d s" % int(idle_quit_s))
		idle_quit_s = 0.0
		quit_func.call()


func _handle(peer: StreamPeerTCP, line: String) -> void:
	_last_activity_ms = Time.get_ticks_msec()
	var msg = JSON.parse_string(line)
	if not (msg is Dictionary):
		_send(peer, {"id": null, "ok": false, "error": "bad json"})
		return
	var id = msg.get("id", null)
	if id is float and id == floor(id):
		id = int(id)
	var args = msg.get("args", {})
	if not (args is Dictionary):
		args = {}
	_busy += 1
	var result = await handler.run_command(str(msg.get("cmd", "")), args)
	_busy -= 1
	_last_activity_ms = Time.get_ticks_msec()
	if result is Dictionary and result.has("error"):
		_send(peer, {"id": id, "ok": false, "error": result.error})
	else:
		_send(peer, {"id": id, "ok": true, "result": result})


func _send(peer: StreamPeerTCP, obj: Dictionary) -> void:
	if peer.get_status() == StreamPeerTCP.STATUS_CONNECTED:
		peer.put_data((JSON.stringify(obj) + "\n").to_utf8_buffer())
