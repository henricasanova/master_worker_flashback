#!/usr/bin/env python3 

import sys
import subprocess
import matplotlib.pyplot as plt

try:
    min_num_workers = int(sys.argv[1])
    max_num_workers = int(sys.argv[2])
    step_num_workers = int(sys.argv[3])
    num_trials = int(sys.argv[4])
except Exception:
    sys.stderr.write(
        f"Usage: {sys.argv[0]} <min num workers (int)> <max num workers (int)> <step num workers (int)> <num trials (int)>\n")
    sys.exit(1)

num_cores_per_host = 8
min_core_speed = 100
max_core_speed = 200
num_links = 100
min_bandwidth = 100
max_bandwidth = 200
route_length = 10
min_computation = 100
max_computation = 200
min_data_size = 100
max_data_size = 100

versions = ["v3_10", "v3_34"]

stack_size_in_kb = 100

results = {}
for version in versions:
    results[version] = {}

num_workers_values = range(min_num_workers, max_num_workers + 1, step_num_workers)

for num_workers in num_workers_values:
    for version in versions:

        # RUN EXPERIMENT
        num_tasks = num_workers * 200
        num_hosts = int(1 + num_workers / num_cores_per_host)

        sys.stderr.write(f"Running with {num_workers} workers...\n")
        times = []
        mems = []
        for seed in range(0, num_trials):

            command = f"docker run -it --rm -w /home/simgrid/build_simgrid_{version}/ -v `pwd`:/home/simgrid simgrid_{version} /usr/bin/time -v ./master_worker_{version} {num_hosts} {num_cores_per_host} {min_core_speed} {max_core_speed} {num_links} {min_bandwidth} {max_bandwidth} {route_length} {num_workers} {num_tasks} {min_computation} {max_computation} {min_data_size} {max_data_size} {seed} --log=root.thresh:critical --cfg=contexts/stack-size:{stack_size_in_kb}"
            print(command)

            try:
                output = subprocess.check_output(command, shell=True).decode('utf-8').splitlines()
            except Exception:
                sys.stderr.write("Out of memory... aborting this experiment")
                continue
            for line in output:
                if "Elapsed (wall clock)" in line:
                    tokens = line.split(":")
                    times.append(float(60.0 * float(tokens[-2]) + float(tokens[-1])))
                elif "Maximum resident set size" in line:
                    tokens = line.split(":")
                    mems.append(float(tokens[-1]) / 1024.0)

        if len(times) == 0 or len(mems) == 0:
            results[version][num_workers] = [0, 0]
        else:
            results[version][num_workers] = [times, mems]


# PLOT RESULTS
fontsize = 12
f, ax1 = plt.subplots(1, 1, sharey=True, figsize=(14, 7))
ax2 = ax1.twinx()
plt.grid(axis='y')

lns_handles = []

print(results)

for version in versions:
    if version == "v3_10":
        line_style = ":"
    else:
        line_style = "-"

    average_times = [sum(results[version][x][0]) / len(results[version][x][0]) for x in num_workers_values]

    lns1 = ax1.plot(num_workers_values, average_times, 'r' + line_style, linewidth=2,
                    label="Simulation Time " + version)
    for num_workers in num_workers_values:
        for time in results[version][num_workers][0]:
            ax1.plot([num_workers], [time], 'xr', linewidth=2)

    average_footprints = [sum(results[version][x][1]) / len(results[version][x][1]) for x in num_workers_values]

    lns2 = ax2.plot(num_workers_values, average_footprints, 'b' + line_style, linewidth=2,
                    label="Maximum RSS " + version)
    for num_workers in num_workers_values:
        for footprint in results[version][num_workers][1]:
            ax2.plot([num_workers], [footprint], 'xb', linewidth=2)

    lns_handles.append(lns1)
    lns_handles.append(lns2)

ax1.set_xlabel("Number of workers", fontsize=fontsize + 1)
ax1.set_ylabel("Time (sec)", fontsize=fontsize + 1)
ax2.set_ylabel("Memory Footprint (MB)", fontsize=fontsize + 1)

ax1.tick_params(axis='x', labelsize=fontsize)
ax1.tick_params(axis='y', labelsize=fontsize)
ax2.tick_params(axis='y', labelsize=fontsize)

lns = lns_handles[0] + lns_handles[1] + lns_handles[2] + lns_handles[3]
labs = [l.get_label() for l in lns]
ax1.legend(lns, labs, loc=0, fontsize=fontsize)

figname = f"simgrid_master_worker_{num_workers_values[0]}_{num_workers_values[-1]}.pdf"
plt.savefig(figname)
print("Figure saved to: " + figname)
