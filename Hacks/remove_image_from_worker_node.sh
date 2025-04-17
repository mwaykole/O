#!/bin/bash

# Get only worker nodes (nodes without the master/control-plane role)
WORKER_NODES=$(oc get nodes -l '!node-role.kubernetes.io/master' -o jsonpath='{.items[*].metadata.name}')

# Check if we got any worker nodes
if [ -z "$WORKER_NODES" ]; then
    echo "Error: No worker nodes found in the cluster"
    exit 1
fi

echo "Found worker nodes: $WORKER_NODES"
echo "Starting Podman image cleanup on worker nodes..."
echo ""

# Function to clean images on a single node
clean_worker_node() {
    local NODE=$1
    echo "Processing worker node: $NODE"

    oc debug node/$NODE --quiet -- chroot /host /bin/bash -c "
        echo 'Current Podman images on $NODE:';
        podman images --format 'table {{.ID}}\t{{.Repository}}:{{.Tag}}' || echo 'No images found';
        echo 'Removing all images...';
        podman rmi -a -f 2>/dev/null || echo 'No images to remove';
        echo 'Verifying cleanup:';
        podman images || echo 'No images remaining';
        echo 'Done on $NODE'
    " 2>&1 | sed "s/^/[${NODE}] /"

    echo "----------------------------------------"
}

# Process worker nodes in parallel (max 3 at a time for safety)
export -f clean_worker_node
echo "$WORKER_NODES" | tr ' ' '\n' | xargs -P3 -I{} bash -c 'clean_worker_node "$@"' _ {}

echo "Podman image cleanup completed on all worker nodes"