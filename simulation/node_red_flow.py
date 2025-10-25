[
  {
    "id": "ingest",
    "type": "http in",
    "z": "flow",
    "name": "",
    "url": "/ingest",
    "method": "post",
    "x": 120,
    "y": 80,
    "wires": [["map"]]
  },
  {
    "id": "map",
    "type": "function",
    "name": "Map -> Weaviate",
    "func": "msg.method = \"POST\";\nmsg.url = \"http://localhost:8080/v1/objects\";\nmsg.headers = {\"Content-Type\":\"application/json\"};\nconst body = {\n    class: \"SensorEvent\",\n    properties: {\n        timestamp: new Date().toISOString(),\n        node_id: msg.payload.node_id || 'node_unknown',\n        methane_ppm: Number(msg.payload.methane_ppm || 0),\n        scenario: msg.payload.scenario || 'nr',\n        trace_id: 'nr-' + Date.now()\n    }\n};\nmsg.payload = body;\nreturn msg;",
    "outputs": 1,
    "wires": [["http_request"]]
  },
  {
    "id": "http_request",
    "type": "http request",
    "name": "Weaviate Insert",
    "method": "POST",
    "ret": "txt",
    "url": "http://localhost:8080/v1/objects",
    "wires": [["http_response"]]
  },
  {
    "id": "http_response",
    "type": "http response",
    "name": "",
    "wires": []
  }
]
