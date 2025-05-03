const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const cors = require("cors");
const pg = require("pg");
require("dotenv").config();

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: "*" },
});

app.use(cors());
app.use(express.json());

const db = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
});

(async () => {
  await db.query(`
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      password TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS messages (
      id SERIAL PRIMARY KEY,
      sender TEXT NOT NULL,
      recipient TEXT NOT NULL,
      message TEXT NOT NULL,
      timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
  `);
})();

const usersOnline = {};

io.on("connection", (socket) => {
  socket.on("register", (userId) => {
    usersOnline[userId] = socket.id;
  });

  socket.on("send-message", async (data) => {
    const { sender, recipient, message, timestamp } = data;
    await db.query(
      "INSERT INTO messages (sender, recipient, message, timestamp) VALUES ($1, $2, $3, $4)",
      [sender, recipient, message, timestamp]
    );
    const recipientSocket = usersOnline[recipient];
    if (recipientSocket) {
      io.to(recipientSocket).emit("receive-message", data);
    }
  });

  socket.on("disconnect", () => {
    for (let [userId, id] of Object.entries(usersOnline)) {
      if (id === socket.id) {
        delete usersOnline[userId];
        break;
      }
    }
  });
});

app.post("/login", async (req, res) => {
  const { userId, password } = req.body;
  const result = await db.query(
    "SELECT * FROM users WHERE id = $1 AND password = $2",
    [userId, password]
  );
  res.status(result.rows.length > 0 ? 200 : 401).json({
    success: result.rows.length > 0,
  });
});

app.post("/register", async (req, res) => {
  const { userId, password } = req.body;
  try {
    await db.query("INSERT INTO users (id, password) VALUES ($1, $2)", [
      userId,
      password,
    ]);
    res.status(201).json({ success: true });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

server.listen(3001, () => {
  console.log("Server running on http://localhost:3001");
});
