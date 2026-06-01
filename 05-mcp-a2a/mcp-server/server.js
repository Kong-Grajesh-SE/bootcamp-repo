// =============================================================================
// MCP Travel Backend Server
// Supports: MCP JSON-RPC (tools), A2A agent endpoints, content moderation
// Port: 3001 (MCP + A2A) / 4000 (guardrail moderation)
// =============================================================================
const express = require("express");

const app = express();
app.use(express.json());

// ── Sample data ─────────────────────────────────────────────────────────────
const FLIGHTS = [
  { id: "AA100", airline: "American Airlines", origin: "SFO", destination: "LHR", date: "2026-06-15", price: 850, currency: "USD", departure: "08:30", arrival: "02:45+1" },
  { id: "BA287", airline: "British Airways", origin: "SFO", destination: "LHR", date: "2026-06-15", price: 920, currency: "USD", departure: "16:00", arrival: "10:15+1" },
  { id: "UA901", airline: "United Airlines", origin: "SFO", destination: "LHR", date: "2026-06-15", price: 780, currency: "USD", departure: "20:15", arrival: "14:30+1" },
  { id: "DL400", airline: "Delta Airlines", origin: "JFK", destination: "CDG", date: "2026-06-15", price: 650, currency: "USD", departure: "22:00", arrival: "11:30+1" },
];

const HOTELS = [
  { id: "H001", name: "Heathrow Garden Inn", location: "LHR", price_per_night: 120, currency: "USD", rating: 4.2 },
  { id: "H002", name: "London Marriott Heathrow", location: "LHR", price_per_night: 195, currency: "USD", rating: 4.5 },
  { id: "H003", name: "Paris Le Grand Hotel", location: "CDG", price_per_night: 250, currency: "USD", rating: 4.7 },
  { id: "H004", name: "Holiday Inn Express Heathrow", location: "LHR", price_per_night: 89, currency: "USD", rating: 3.9 },
];

const WEATHER = {
  LHR: { airport: "LHR", city: "London", temp_c: 18, condition: "Partly Cloudy", humidity: 65, wind_kph: 15 },
  SFO: { airport: "SFO", city: "San Francisco", temp_c: 16, condition: "Foggy", humidity: 78, wind_kph: 22 },
  JFK: { airport: "JFK", city: "New York", temp_c: 28, condition: "Sunny", humidity: 55, wind_kph: 10 },
  CDG: { airport: "CDG", city: "Paris", temp_c: 22, condition: "Clear", humidity: 50, wind_kph: 12 },
};

const bookings = [];

// ── MCP Tool Definitions ────────────────────────────────────────────────────
const MCP_TOOLS = [
  {
    name: "search_flights",
    description: "Search available flights between airports on a given date",
    inputSchema: {
      type: "object",
      properties: {
        origin: { type: "string", description: "Origin airport code (e.g. SFO)" },
        destination: { type: "string", description: "Destination airport code (e.g. LHR)" },
        date: { type: "string", description: "Travel date (YYYY-MM-DD)" },
      },
      required: ["origin", "destination"],
    },
  },
  {
    name: "book_flight",
    description: "Book a specific flight for a passenger",
    inputSchema: {
      type: "object",
      properties: {
        flight_id: { type: "string", description: "Flight ID to book (e.g. AA100)" },
        passenger: { type: "string", description: "Passenger full name" },
      },
      required: ["flight_id", "passenger"],
    },
  },
  {
    name: "get_weather",
    description: "Get current weather conditions at an airport",
    inputSchema: {
      type: "object",
      properties: {
        airport: { type: "string", description: "Airport code (e.g. LHR)" },
      },
      required: ["airport"],
    },
  },
  {
    name: "search_hotels",
    description: "Search hotels near an airport location",
    inputSchema: {
      type: "object",
      properties: {
        location: { type: "string", description: "Airport code or city (e.g. LHR)" },
        nights: { type: "number", description: "Number of nights" },
      },
      required: ["location"],
    },
  },
  {
    name: "book_hotel",
    description: "Book a hotel room",
    inputSchema: {
      type: "object",
      properties: {
        hotel_id: { type: "string", description: "Hotel ID to book (e.g. H001)" },
        guest: { type: "string", description: "Guest full name" },
        nights: { type: "number", description: "Number of nights" },
      },
      required: ["hotel_id", "guest"],
    },
  },
];

// ── Tool execution logic ────────────────────────────────────────────────────
function executeTool(name, args) {
  switch (name) {
    case "search_flights": {
      let results = FLIGHTS;
      if (args.origin) results = results.filter((f) => f.origin === args.origin.toUpperCase());
      if (args.destination) results = results.filter((f) => f.destination === args.destination.toUpperCase());
      if (args.date) results = results.filter((f) => f.date === args.date);
      return results;
    }
    case "book_flight": {
      const flight = FLIGHTS.find((f) => f.id === args.flight_id);
      if (!flight) return { error: `Flight ${args.flight_id} not found` };
      const booking = { confirmation: `BK-${Date.now()}`, flight, passenger: args.passenger, status: "confirmed" };
      bookings.push(booking);
      return booking;
    }
    case "get_weather": {
      const code = (args.airport || "").toUpperCase();
      return WEATHER[code] || { error: `No weather data for ${code}` };
    }
    case "search_hotels": {
      const loc = (args.location || "").toUpperCase();
      let results = HOTELS.filter((h) => h.location === loc);
      if (args.nights) results = results.map((h) => ({ ...h, total: h.price_per_night * args.nights, nights: args.nights }));
      return results;
    }
    case "book_hotel": {
      const hotel = HOTELS.find((h) => h.id === args.hotel_id);
      if (!hotel) return { error: `Hotel ${args.hotel_id} not found` };
      const nights = args.nights || 1;
      const booking = { confirmation: `HB-${Date.now()}`, hotel, guest: args.guest, nights, total: hotel.price_per_night * nights, status: "confirmed" };
      bookings.push(booking);
      return booking;
    }
    default:
      return null;
  }
}

// ── MCP JSON-RPC endpoint ───────────────────────────────────────────────────
app.post("/mcp/tools", (req, res) => {
  const { jsonrpc, id, method, params } = req.body;

  if (jsonrpc !== "2.0") {
    return res.status(400).json({ jsonrpc: "2.0", id, error: { code: -32600, message: "Invalid JSON-RPC version" } });
  }

  switch (method) {
    case "initialize":
      return res.json({
        jsonrpc: "2.0",
        id,
        result: {
          protocolVersion: "2024-11-05",
          capabilities: { tools: {} },
          serverInfo: { name: "travel-mcp-server", version: "1.0.0" },
        },
      });

    case "tools/list":
      return res.json({ jsonrpc: "2.0", id, result: { tools: MCP_TOOLS } });

    case "tools/call": {
      const { name, arguments: args } = params || {};
      const tool = MCP_TOOLS.find((t) => t.name === name);
      if (!tool) {
        return res.json({ jsonrpc: "2.0", id, error: { code: -32602, message: `Unknown tool: ${name}` } });
      }
      const result = executeTool(name, args || {});
      return res.json({
        jsonrpc: "2.0",
        id,
        result: { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] },
      });
    }

    case "resources/list":
      return res.json({ jsonrpc: "2.0", id, result: { resources: [] } });

    case "prompts/list":
      return res.json({ jsonrpc: "2.0", id, result: { prompts: [] } });

    default:
      return res.json({ jsonrpc: "2.0", id, error: { code: -32601, message: `Method not found: ${method}` } });
  }
});

// SSE / Streamable HTTP support (GET)
app.get("/mcp/tools", (req, res) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.write(`data: ${JSON.stringify({ type: "endpoint", url: "/mcp/tools" })}\n\n`);
});

// ── A2A Agent Card ──────────────────────────────────────────────────────────
const AGENT_CARD = {
  name: "TravelOrchestratorAgent",
  description: "Multi-skill travel planning agent",
  url: "http://localhost:8000/.well-known/agent.json",
  version: "1.0.0",
  capabilities: { streaming: false, pushNotifications: false },
  skills: [
    { id: "flight-search", name: "Search Flights", description: "Search available flights between airports", inputModes: ["text"], outputModes: ["text", "data"] },
    { id: "hotel-booking", name: "Book Hotels", description: "Search and book hotel rooms", inputModes: ["text"], outputModes: ["text", "data"] },
    { id: "weather-check", name: "Check Weather", description: "Get weather conditions at airports", inputModes: ["text"], outputModes: ["text", "data"] },
  ],
  authentication: { schemes: ["bearer"] },
};

app.get("/.well-known/agent.json", (req, res) => res.json(AGENT_CARD));
app.get("/a2a/agents", (req, res) => res.json(AGENT_CARD.skills));

// ── A2A sub-agent endpoints ─────────────────────────────────────────────────
function handleA2A(toolName, req, res) {
  const { id, message } = req.body;
  const text = message?.parts?.[0]?.text || "";

  // Parse simple intent from text
  let result;
  switch (toolName) {
    case "flights": {
      const originMatch = text.match(/\b([A-Z]{3})\b/);
      const destMatch = text.match(/\b([A-Z]{3})\b/g);
      const origin = originMatch ? originMatch[0] : null;
      const destination = destMatch && destMatch.length > 1 ? destMatch[1] : null;
      result = executeTool("search_flights", { origin, destination });
      break;
    }
    case "hotels": {
      const locMatch = text.match(/\b([A-Z]{3})\b/);
      result = executeTool("search_hotels", { location: locMatch ? locMatch[0] : "" });
      break;
    }
    case "weather": {
      const airportMatch = text.match(/\b([A-Z]{3})\b/);
      result = executeTool("get_weather", { airport: airportMatch ? airportMatch[0] : "" });
      break;
    }
    default:
      return res.status(404).json({ error: `Unknown agent: ${toolName}` });
  }

  res.json({
    id,
    result: {
      role: "agent",
      parts: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    },
  });
}

app.post("/a2a/flights", (req, res) => handleA2A("flights", req, res));
app.post("/a2a/hotels", (req, res) => handleA2A("hotels", req, res));
app.post("/a2a/weather", (req, res) => handleA2A("weather", req, res));

// ── Health check ────────────────────────────────────────────────────────────
app.get("/health", (req, res) => res.json({ status: "ok", services: ["mcp", "a2a"] }));

// ── Start server ────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`MCP Travel Backend running on http://localhost:${PORT}`);
  console.log(`  MCP endpoint:    POST http://localhost:${PORT}/mcp/tools`);
  console.log(`  A2A Agent Card:  GET  http://localhost:${PORT}/.well-known/agent.json`);
  console.log(`  A2A Flights:     POST http://localhost:${PORT}/a2a/flights`);
  console.log(`  A2A Hotels:      POST http://localhost:${PORT}/a2a/hotels`);
  console.log(`  A2A Weather:     POST http://localhost:${PORT}/a2a/weather`);
});
