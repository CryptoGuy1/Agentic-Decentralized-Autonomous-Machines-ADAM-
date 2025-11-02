[
    {
        "id": "1a2b3c4d5e6f7g8h",
        "type": "tab",
        "label": "Methane Simulation Flow",
        "disabled": false,
        "info": ""
    },
    {
        "id": "inject1",
        "type": "inject",
        "z": "1a2b3c4d5e6f7g8h",
        "name": "Trigger Every 5s",
        "props": [
            {
                "p": "payload"
            }
        ],
        "repeat": "5",
        "once": true,
        "onceDelay": "1",
        "topic": "",
        "payload": "{\"sensor_id\":\"CH4_001\"}",
        "payloadType": "json",
        "x": 140,
        "y": 120,
        "wires": [
            [
                "function1"
            ]
        ]
    },
    {
        "id": "function1",
        "type": "function",
        "z": "1a2b3c4d5e6f7g8h",
        "name": "Generate Random Methane Data",
        "func": "msg.payload.methane_ppm = (Math.random() * 100).toFixed(2);\nmsg.payload.timestamp = new Date().toISOString();\nreturn msg;",
        "outputs": 1,
        "noerr": 0,
        "initialize": "",
        "finalize": "",
        "libs": [],
        "x": 400,
        "y": 120,
        "wires": [
            [
                "http1",
                "debug1"
            ]
        ]
    },
    {
        "id": "http1",
        "type": "http request",
        "z": "1a2b3c4d5e6f7g8h",
        "name": "Send to Weaviate",
        "method": "POST",
        "ret": "txt",
        "paytoqs": "ignore",
        "url": "http://localhost:8080/v1/objects",
        "tls": "",
        "persist": false,
        "proxy": "",
        "authType": "",
        "senderr": false,
        "headers": {
            "Content-Type": "application/json"
        },
        "x": 670,
        "y": 120,
        "wires": [
            [
                "debug2"
            ]
        ]
    },
    {
        "id": "debug1",
        "type": "debug",
        "z": "1a2b3c4d5e6f7g8h",
        "name": "Simulated Output",
        "active": true,
        "tosidebar": true,
        "console": false,
        "tostatus": false,
        "complete": "payload",
        "targetType": "msg",
        "x": 420,
        "y": 200,
        "wires": []
    },
    {
        "id": "debug2",
        "type": "debug",
        "z": "1a2b3c4d5e6f7g8h",
        "name": "Weaviate Response",
        "active": true,
        "tosidebar": true,
        "console": false,
        "tostatus": false,
        "complete": "payload",
        "targetType": "msg",
        "x": 870,
        "y": 120,
        "wires": []
    }
]