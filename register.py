#############
# Registers all docker services in a swarm cluster in etcd
# Has to be run on swarm master.
# Generates JSON for each service like:
# { "name": "service_name", "address": "service_name:target_port", ... all serice labels ... }

import etcd, os, json, time, docker

def update(etcdc, dockerc, base_dir):	
	old_services = []
	try:
		services_dir = etcdc.read(base_dir, recursive=True, sorted=True)
		for child in services_dir.children:
			old_services.append(child.key)
	except:
		print("No prevoius services found.")

	for service in dockerc.services.list():
		descr = { "name": service.name }
		endpoint = service.attrs['Endpoint']

		if 'Ports' in endpoint:
			ports = endpoint['Ports']
			if len(ports) > 0 and 'TargetPort' in ports[0]:
				descr['address'] = '{0}:{1}'.format(service.name, ports[0]['TargetPort'])
		
		spec = service.attrs['Spec']
		if 'Labels' in spec:
			descr.update(spec['Labels'])

		etcd_key = '{0}/{1}'.format(base_dir, service.name)
		etcdc.write(etcd_key, json.dumps(descr))

		if etcd_key in old_services:
			old_services.remove(etcd_key)
		else:
			print("New service added:", descr)

	for to_remove in old_services:
		print('Unregistering service {0}'.format(to_remove))
		try:
			etcdc.delete(to_remove)
		except:
			print("Failed to unregister a service")

def main_loop():
	etcd_host = os.environ.get('ETCD_HOST','etcd')
	etcd_port = int(os.environ.get('ETCD_PORT','2379'))	
	base_dir = os.environ.get('BASE_DIR','/services')

	interval = int(os.environ.get('UPDATE_INTERVAL','120'))
	infinite_run = os.environ.get('RUN_ONCE', 'False') == 'False'

	print('etcd: {0}:{1}, base_dir: {2}, run_once: {3}, update_interval: {4}'.format(etcd_host, etcd_port, base_dir, not infinite_run, interval))

	etcdClient = etcd.Client(host=etcd_host, port=etcd_port)
	dockerClient = docker.DockerClient(base_url='unix://var/run/docker.sock')

	while infinite_run:
		try:
			update(etcdClient, dockerClient, base_dir)
		except:
			print("Failed to update services")

		time.sleep(interval)


if __name__ == '__main__':
	try:
		main_loop()
	except KeyboardInterrupt:
		print('Exiting')
		sys.exit(0)		