from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json

_backendImage = "jdob/visitors-service:latest"
_frontendImage = "jdob/visitors-webui:1.0.0"
_default_size = 1
_default_title = "Visitors Dashboard"

_mysql_manifest = [
  {
    "apiVersion": "v1",
    "kind": "Secret",
    "metadata": {
      "name": "mysql-auth"
    },
    "type": "Opaque",
    "stringData": {
      "username": "visitors-user",
      "password": "visitors-pass"
    }
  },
  {
    "apiVersion": "apps/v1",
    "kind": "Deployment",
    "metadata": {
      "name": "mysql"
    },
    "spec": {
      "replicas": 1,
      "selector": {
        "matchLabels": {
          "app": "visitors",
          "tier": "mysql"
        }
      },
      "template": {
        "metadata": {
          "labels": {
            "app": "visitors",
            "tier": "mysql"
          }
        },
        "spec": {
          "containers": [
            {
              "name": "visitors-mysql",
              "image": "mysql:5.7",
              "imagePullPolicy": "Always",
              "ports": [
                {
                  "name": "mysql",
                  "containerPort": 3306,
                  "protocol": "TCP"
                }
              ],
              "env": [
                {
                  "name": "MYSQL_ROOT_PASSWORD",
                  "value": "password"
                },
                {
                  "name": "MYSQL_DATABASE",
                  "value": "visitors_db"
                },
                {
                  "name": "MYSQL_USER",
                  "valueFrom": {
                    "secretKeyRef": {
                      "name": "mysql-auth",
                      "key": "username"
                    }
                  }
                },
                {
                  "name": "MYSQL_PASSWORD",
                  "valueFrom": {
                    "secretKeyRef": {
                      "name": "mysql-auth",
                      "key": "password"
                    }
                  }
                }
              ]
            }
          ]
        }
      }
    }
  },
  {
    "apiVersion": "v1",
    "kind": "Service",
    "metadata": {
      "name": "mysql-service",
      "labels": {
        "app": "visitors",
        "tier": "mysql"
      }
    },
    "spec": {
      "clusterIP": "None",
      "ports": [
        {
          "port": 3306
        }
      ],
      "selector": {
        "app": "visitors",
        "tier": "mysql"
      }
    }
  }
]

_backend_manifest = [
  {
    "apiVersion": "apps/v1",
    "kind": "Deployment",
    "metadata": {
      "name": "visitors-backend"
    },
    "spec": {
      "replicas": _default_size,
      "selector": {
        "matchLabels": {
          "app": "visitors",
          "tier": "backend"
        }
      },
      "template": {
        "metadata": {
          "labels": {
            "app": "visitors",
            "tier": "backend"
          }
        },
        "spec": {
          "containers": [
            {
              "name": "visitors-backend",
              "image": _backendImage,
              "imagePullPolicy": "Always",
              "ports": [
                {
                  "name": "visitors",
                  "containerPort": 8000
                }
              ],
              "env": [
                {
                  "name": "MYSQL_DATABASE",
                  "value": "visitors_db"
                },
                {
                  "name": "MYSQL_SERVICE_HOST",
                  "value": "mysql-service"
                },
                {
                  "name": "MYSQL_USERNAME",
                  "valueFrom": {
                    "secretKeyRef": {
                      "name": "mysql-auth",
                      "key": "username"
                    }
                  }
                },
                {
                  "name": "MYSQL_PASSWORD",
                  "valueFrom": {
                    "secretKeyRef": {
                      "name": "mysql-auth",
                      "key": "password"
                    }
                  }
                }
              ]
            }
          ]
        }
      }
    }
  },
  {
    "apiVersion": "v1",
    "kind": "Service",
    "metadata": {
      "name": "visitors-backend-service",
      "labels": {
        "app": "visitors",
        "tier": "backend"
      }
    },
    "spec": {
      "type": "NodePort",
      "ports": [
        {
          "port": 8000,
          "targetPort": 8000,
          "nodePort": 30685,
          "protocol": "TCP"
        }
      ],
      "selector": {
        "app": "visitors",
        "tier": "backend"
      }
    }
  }
]

_frontend_manifest = [
  {
    "apiVersion": "apps/v1",
    "kind": "Deployment",
    "metadata": {
      "name": "visitors-frontend"
    },
    "spec": {
      "replicas": 1,
      "selector": {
        "matchLabels": {
          "app": "visitors",
          "tier": "frontend"
        }
      },
      "template": {
        "metadata": {
          "labels": {
            "app": "visitors",
            "tier": "frontend"
          }
        },
        "spec": {
          "containers": [
            {
              "name": "visitors-frontend",
              "image": _frontendImage,
              "imagePullPolicy": "Always",
              "ports": [
                {
                  "name": "visitors",
                  "containerPort": 3000
                }
              ],
              "env": [
                {
                  "name": "REACT_APP_TITLE",
                  "value": _default_title
                }
              ]
            }
          ]
        }
      }
    }
  },
  {
    "apiVersion": "v1",
    "kind": "Service",
    "metadata": {
      "name": "visitors-frontend-service",
      "labels": {
        "app": "visitors",
        "tier": "frontend"
      }
    },
    "spec": {
      "type": "NodePort",
      "ports": [
        {
          "port": 3000,
          "targetPort": 3000,
          "nodePort": 30686,
          "protocol": "TCP"
        }
      ],
      "selector": {
        "app": "visitors",
        "tier": "frontend"
      }
    }
  }
]

class Controller(BaseHTTPRequestHandler):
  def sync(self, parent, children):
    # Compute status based on observed state.
    desired_status = {
      "backendImage": _backendImage,
      "frontendImage": _frontendImage
    }

    desired_objs = _mysql_manifest

    # Check if mysql is up
    if not children["Deployment.apps/v1"].has_key("visitors-mysql"):
      return {"status": desired_status, "children": desired_objs, "resyncAfterSeconds": 5}

    _backend_manifest[0]["spec"]["replicas"] = parent.get("sepc", {}).get("size", _default_size)
    desired_objs.extend(_backend_manifest)

    _frontend_manifest[0]["spec"]["template"]["spec"]["containers"][0]["env"][0].value = parent.get("sepc", {}).get("title", _default_title)
    desired_objs.extend(_frontend_manifest)

    return {"status": desired_status, "children": desired_objs}

  def do_POST(self):
    # Serve the sync() function as a JSON webhook.
    observed = json.loads(self.rfile.read(int(self.headers.getheader("content-length"))))
    desired = self.sync(observed["parent"], observed["children"])

    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.end_headers()
    self.wfile.write(json.dumps(desired))

HTTPServer(("", 80), Controller).serve_forever()