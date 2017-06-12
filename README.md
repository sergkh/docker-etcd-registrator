# docker-etcd-registrator

[![Build Status](https://travis-ci.org/sergkh/docker-etcd-registrator.svg?branch=master)](https://travis-ci.org/sergkh/docker-etcd-registrator)

[Docker Hub](https://hub.docker.com/r/sergkh/docker-etcd-registrator/)

Registers all swarm services in a etcd in a format suitable for [nginx-autoproxy](https://hub.docker.com/r/sergkh/nginx-autoproxy/). Services are registered at key: `/services/:service_name`.

Services are put into `BASE_DIR`/{service_name} key in the JSON format. Json contains following fields:

```json
{
  "name": "{service_name}",
  "address": "{service_name}:{published_port}",
  "Env": [ "copy of service environment variables" ],
  "{docker_service_label}": "{label_value}"
}
```

Example:

```json
{
  "name": "play_app",
  "address": "play_app:9000",
  "Env": [ "DEBUG=true", "DB_HOST=mysql" ],
  "test_label": "foo"
}
```

If docker service is removed it will also be removed from the `etcd`. But the actual number of containers for specific service is ignored.

Run steps:
1. Create a swarm cluster.
2. Start etcd service:
```
docker service create --name etcd \
  --network swarm_network \
  --publish 2380 --publish 2379:2379 \ 
  quay.io/coreos/etcd:latest etcd \
    -advertise-client-urls http://etcd:2379 \
    -listen-client-urls http://0.0.0.0:2379
```

3. Run registrator on a swarm manager:

```
docker service create --name registrator \
  --network swarm_network \
  --constraint 'node.role == manager' \
  --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
  --env ETCD_HOST=etcd --env ETCD_PORT=2379 \
  sergkh/docker-etcd-registrator
```

# Configuration options

Configuration can be set using following environment variables:

* `ETCD_HOST` – Etcd daemon host (default: etcd)
* `ETCD_PORT` – Etcd daemon port (default: 2379)
* `BASE_DIR`  – Base directroy in the etcd where services will be registered (default: `/services`)
* `UPDATE_INTERVAL` – Docker polling interval in seconds (default: 120)
* `RUN_ONCE` – Stops container after services update. Possible values are: `True/False` (default: `False`)

# Ignoring a service

Service can be ignored by simply adding a label `registry_ignore`:

```
docker service create --name kafka --label registry_ignore wurstmeister/kafka
```

# Contributions

Contributions are welcomed. Thanks [@fsanaulla](https://github.com/fsanaulla) for his contributions.

