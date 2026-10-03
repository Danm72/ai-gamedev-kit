// Small JSON reader and writer for the bridge. JsonUtility cannot read a free-form object.
// Objects become Dictionary<string, object>, arrays List<object>, numbers double.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace GameBridge
{
	public static class MiniJson
	{
		public static object Parse(string s)
		{
			int i = 0;
			object v = Value(s, ref i);
			Ws(s, ref i);
			if (i != s.Length) throw new FormatException("trailing text at " + i);
			return v;
		}

		static void Ws(string s, ref int i) { while (i < s.Length && char.IsWhiteSpace(s[i])) i++; }

		static object Value(string s, ref int i)
		{
			Ws(s, ref i);
			if (i >= s.Length) throw new FormatException("unexpected end");
			char c = s[i];
			if (c == '{')
			{
				var d = new Dictionary<string, object>();
				i++; Ws(s, ref i);
				if (s[i] == '}') { i++; return d; }
				while (true)
				{
					Ws(s, ref i);
					string k = Str(s, ref i);
					Ws(s, ref i);
					if (s[i++] != ':') throw new FormatException("':' expected at " + (i - 1));
					d[k] = Value(s, ref i);
					Ws(s, ref i);
					if (s[i] == ',') { i++; continue; }
					if (s[i++] == '}') return d;
					throw new FormatException("',' or '}' expected at " + (i - 1));
				}
			}
			if (c == '[')
			{
				var l = new List<object>();
				i++; Ws(s, ref i);
				if (s[i] == ']') { i++; return l; }
				while (true)
				{
					l.Add(Value(s, ref i));
					Ws(s, ref i);
					if (s[i] == ',') { i++; continue; }
					if (s[i++] == ']') return l;
					throw new FormatException("',' or ']' expected at " + (i - 1));
				}
			}
			if (c == '"') return Str(s, ref i);
			if (s.Length - i >= 4 && s.Substring(i, 4) == "true") { i += 4; return true; }
			if (s.Length - i >= 5 && s.Substring(i, 5) == "false") { i += 5; return false; }
			if (s.Length - i >= 4 && s.Substring(i, 4) == "null") { i += 4; return null; }
			int st = i;
			while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
			if (st == i) throw new FormatException("bad value at " + st);
			return double.Parse(s.Substring(st, i - st), CultureInfo.InvariantCulture);
		}

		static string Str(string s, ref int i)
		{
			if (s[i] != '"') throw new FormatException("string expected at " + i);
			var sb = new StringBuilder();
			i++;
			while (s[i] != '"')
			{
				char c = s[i++];
				if (c != '\\') { sb.Append(c); continue; }
				char e = s[i++];
				switch (e)
				{
					case 'n': sb.Append('\n'); break;
					case 't': sb.Append('\t'); break;
					case 'r': sb.Append('\r'); break;
					case 'b': sb.Append('\b'); break;
					case 'f': sb.Append('\f'); break;
					case 'u': sb.Append((char)Convert.ToInt32(s.Substring(i, 4), 16)); i += 4; break;
					default: sb.Append(e); break;
				}
			}
			i++;
			return sb.ToString();
		}

		public static string Write(object v)
		{
			var sb = new StringBuilder();
			W(sb, v);
			return sb.ToString();
		}

		static void W(StringBuilder sb, object v)
		{
			switch (v)
			{
				case null: sb.Append("null"); return;
				case bool b: sb.Append(b ? "true" : "false"); return;
				case string s: Q(sb, s); return;
				// Through the shortest float text, so 0.1f writes 0.1 and not 0.100000001490116.
				case float f: Num(sb, double.Parse(f.ToString("R", CultureInfo.InvariantCulture), CultureInfo.InvariantCulture)); return;
				case double d: Num(sb, d); return;
				case int n: sb.Append(n.ToString(CultureInfo.InvariantCulture)); return;
				case long n: sb.Append(n.ToString(CultureInfo.InvariantCulture)); return;
				case IDictionary<string, object> d:
					sb.Append('{');
					bool first = true;
					foreach (var kv in d)
					{
						if (!first) sb.Append(',');
						first = false;
						Q(sb, kv.Key); sb.Append(':'); W(sb, kv.Value);
					}
					sb.Append('}');
					return;
				case IEnumerable e:
					sb.Append('[');
					bool f1 = true;
					foreach (var x in e) { if (!f1) sb.Append(','); f1 = false; W(sb, x); }
					sb.Append(']');
					return;
				default: Q(sb, v.ToString()); return;
			}
		}

		static void Num(StringBuilder sb, double d)
		{
			if (double.IsNaN(d) || double.IsInfinity(d)) { sb.Append("null"); return; }
			// A double keeps its point (300.0), as Godot's JSON.stringify does for a float, so a Python check
			// of isinstance(x, float) holds. An int or long writes no point. A parsed number is a double, so an
			// echoed id writes 3.0, as bridge.gd echoes Godot's float id.
			string t = d.ToString("R", CultureInfo.InvariantCulture);
			sb.Append(t.IndexOf('.') >= 0 || t.IndexOf('E') >= 0 ? t : t + ".0");
		}

		static void Q(StringBuilder sb, string s)
		{
			sb.Append('"');
			foreach (char c in s)
			{
				if (c == '"') sb.Append("\\\"");
				else if (c == '\\') sb.Append("\\\\");
				else if (c == '\n') sb.Append("\\n");
				else if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4"));
				else sb.Append(c);
			}
			sb.Append('"');
		}
	}
}
