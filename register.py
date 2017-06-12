#############
# Registers all docker services in a swarm cluster in etcd
# Has to be run on a swarm master.
# Generates JSON for each service like:
# { "name": "service_name", "address": "service_name:target_port", ... all service labels ... }

import sys, os, time, json, etcd, docker

def update(etcdc, dockerc, base_dir):
    old_services = dict()
    try:
        services_dir = etcdc.read(base_dir, recursive=True, sorted=True)
        for child in services_dir.children:
            old_services[child.key] = child.value
    except:
        print("No prevoius services found.", sys.exc_info()[0])

    for service in dockerc.services.list():
        descr = {"name": service.name}
        endpoint = service.attrs['Endpoint']
        spec = service.attrs['Spec']

        # ignore service when ignore label is set
        if 'Labels' in spec and 'registry_ignore' in spec['Labels']:
            continue

        if 'Ports' in endpoint:
            ports = endpoint['Ports']
            if len(ports) > 0 and 'TargetPort' in ports[0]:
                descr['address'] = '{0}:{1}'.format(service.name, ports[0]['TargetPort'])

        if 'Labels' in spec:
            descr.update(spec['Labels'])

        if 'TaskTemplate' in spec and 'ContainerSpec' in spec['TaskTemplate']:
            container_spec = spec['TaskTemplate']['ContainerSpec']
            if 'Env' in container_spec:
                descr['Env'] = container_spec['Env']

        etcd_key = '{0}/{1}'.format(base_dir, service.name)
        descr_json = json.dumps(descr)

        if etcd_key in old_services:
            if not descr_json == old_services[etcd_key]:
                print("Service {0} updated: {1}".format(service.name, descr_json))
                etcdc.write(etcd_key, descr_json)
            del old_services[etcd_key]
        else:
            try:
                etcdc.set(etcd_key, descr_json)
                print("New service added: {0} with data: {1}".format(descr, descr_json))
            except:
                print("Can't set a value: {0} to a key: {1}:".format(descr_json, etcd_key), sys.exc_info()[0])

    for to_remove in old_services:
        print('Unregistering service {0}'.format(to_remove))
        try:
            etcdc.delete(to_remove)
        except:
            print("Failed to unregister a service {0}:".format(to_remove), sys.exc_info()[0])

def main_loop():
    etcd_host = os.environ.get('ETCD_HOST', 'etcd')
    etcd_port = int(os.environ.get('ETCD_PORT', '2379'))
    base_dir = os.environ.get('BASE_DIR', '/services')

    interval = int(os.environ.get('UPDATE_INTERVAL', '120'))
    infinite_run = os.environ.get('RUN_ONCE', 'False') == 'False'

    print('etcd: {0}:{1}, base_dir: {2}, run_once: {3}, update_interval: {4}'.format(etcd_host, etcd_port, base_dir, not infinite_run, interval))

    etcd_client = etcd.Client(host=etcd_host, port=etcd_port)
    docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')

    while infinite_run:
        try:
            update(etcd_client, docker_client, base_dir)
        except:
            print("Failed to update services: ", sys.exc_info()[0])

        time.sleep(interval)


if __name__ == '__main__':
    try:
        main_loop()
    except KeyboardInterrupt:
        print('Exiting')
        sys.exit(0)
