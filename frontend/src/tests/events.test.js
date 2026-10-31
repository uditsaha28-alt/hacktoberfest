import { subscribeToRun } from "../api/events.js";

/** Minimal EventSource stand-in that lets a test push events by hand. */
class FakeEventSource {
  static last = null;
  constructor(url) {
    this.url = url;
    this.closed = false;
    this.listeners = {};
    FakeEventSource.last = this;
  }
  addEventListener(type, fn) {
    (this.listeners[type] ||= []).push(fn);
  }
  close() {
    this.closed = true;
  }
  emit(type, data) {
    for (const fn of this.listeners[type] || []) fn(data === undefined ? {} : { data });
  }
}

const setup = () => {
  const received = [];
  const close = subscribeToRun("run1", (name, data) => received.push([name, data]), {
    EventSourceImpl: FakeEventSource,
  });
  return { received, close, es: FakeEventSource.last };
};

describe("subscribeToRun", () => {
  it("connects to the run's events url", () => {
    const { es } = setup();
    expect(es.url).toContain("/api/runs/run1/events");
  });

  it("relays parsed events in order", () => {
    const { received, es } = setup();
    es.emit("plan", JSON.stringify({ steps: ["a"] }));
    es.emit("tool_call", JSON.stringify({ id: "t1", tool: "read_file", args: {} }));
    expect(received.map((r) => r[0])).toEqual(["plan", "tool_call"]);
    expect(received[0][1]).toEqual({ steps: ["a"] });
  });

  it("closes the stream after done", () => {
    const { received, es } = setup();
    es.emit("done", "{}");
    expect(es.closed).toBe(true);
    expect(received).toEqual([["done", {}]]);
  });

  it("closes after a contract error event and forwards its message", () => {
    const { received, es } = setup();
    es.emit("error", JSON.stringify({ message: "nope" }));
    expect(es.closed).toBe(true);
    expect(received).toEqual([["error", { message: "nope" }]]);
  });

  it("reports a dropped connection once and closes (no auto-reconnect)", () => {
    const { received, es } = setup();
    es.emit("error"); // native connection error: no data
    es.emit("error");
    expect(es.closed).toBe(true);
    expect(received).toHaveLength(1);
    expect(received[0][0]).toBe("error");
  });

  it("skips malformed JSON without throwing", () => {
    const { received, es } = setup();
    es.emit("plan", "{not json");
    expect(received).toHaveLength(0);
    expect(es.closed).toBe(false);
  });

  it("returns a close function that is safe to call twice", () => {
    const { close, es } = setup();
    close();
    close();
    expect(es.closed).toBe(true);
  });

  it("ignores events after close", () => {
    const { received, close, es } = setup();
    close();
    es.emit("plan", JSON.stringify({ steps: ["x"] }));
    expect(received).toHaveLength(0);
  });
});
