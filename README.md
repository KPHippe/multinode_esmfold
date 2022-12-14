# Multinode ESMFold 

Allows esmfold to be run across multiple nodes (4 instances per node) on Polaris



### Example submission script
```
#!/bin/sh
#PBS -l select=16:system=polaris
#PBS -l walltime=06:00:00
#PBS -l place=scatter
#PBS -q GordonBell
#PBS -A RL-fold
#PBS -l filesystems=home:eagle

# Controlling the output of your application
# UG Sec 3.3 page UG-40 Managing Output and Error Files
# By default, PBS spools your output on the compute node and then uses scp to move it the
# destination directory after the job finishes.  Since we have globally mounted file systems
# it is highly recommended that you use the -k option to write directly to the destination
# the doe stands for direct, output, error
#PBS -k doe
#PBS -o /lus/eagle/projects/CVD-Mol-AI/hippekp/visualization_structures/mdh_submit/mdh_esmfold_submit_run7.out
#PBS -e /lus/eagle/projects/CVD-Mol-AI/hippekp/visualization_structures/mdh_submit/mdh_esmfold_submit_run7.err

# Internet access on nodes
export HTTP_PROXY=http://proxy.alcf.anl.gov:3128
export HTTPS_PROXY=http://proxy.alcf.anl.gov:3130
export http_proxy=http://proxy.alcf.anl.gov:3128
export https_proxy=http://proxy.alcf.anl.gov:3128
git config --global http.proxy http://proxy.alcf.anl.gov:3128
echo "Set HTTP_PROXY and to $HTTP_PROXY"

# Set ADDR and PORT for communication
master_node=$(cat $PBS_NODEFILE | head -1)
export MASTER_ADDR=$(host $master_node | head -1 | awk '{print $4}')
export MASTER_PORT=2345

# Enable GPU-MPI (if supported by application)
export MPICH_GPU_SUPPORT_ENABLED=1

# MPI and OpenMP settings
NNODES=$(wc -l <$PBS_NODEFILE)
NRANKS_PER_NODE=4
NDEPTH=16

NTOTRANKS=$((NNODES * NRANKS_PER_NODE))
echo "NUM_OF_NODES= ${NNODES} TOTAL_NUM_RANKS= ${NTOTRANKS} RANKS_PER_NODE= ${NRANKS_PER_NODE}"
echo <$PBS_NODEFILE

# Change to workdir
cd /lus/eagle/projects/CVD-Mol-AI/hippekp/visualization_structures/mdh/

# Initialize environment
module load conda/2022-09-08
conda activate esmfold
# IMPORTANT NOTE: This requires having a conda environment called gene_transformer

# Logging
echo "$(df -h /dev/shm)"

# For applications that internally handle binding MPI/OpenMP processes to GPUs
mpiexec -n ${NTOTRANKS} --ppn ${NRANKS_PER_NODE} --depth=${NDEPTH} --cpu-bind depth --hostfile $PBS_NODEFILE \
/lus/eagle/projects/CVD-Mol-AI/hippekp/visualization_structures/mdh_submit/proc_per_gpu.sh \
python /lus/eagle/projects/CVD-Mol-AI/hippekp/github/multinode_esmfold/run_polaris.py -f /lus/eagle/projects/CVD-Mol-AI/hippekp/visualization_structures/mdh/all_mdh_proteins_remove_empty.fasta -o /lus/eagle/projects/CVD-Mol-AI/hippekp/visualization_structures/mdh/mdh_structures --cache_dir /lus/eagle/projects/CVD-Mol-AI/hippekp/visualization_structures/esmfold_models
```
