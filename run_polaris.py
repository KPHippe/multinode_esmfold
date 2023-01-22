import re
from pathlib import Path
from argparse import ArgumentParser
import os
from typing import List, Union, Optional
import subprocess
from pydantic import BaseModel

node_rank = int(os.environ.get("NODE_RANK", 0))  # zero indexed
pmi_rank = int(os.environ.get("PMI_RANK", 0))

PathLike = Union[Path, str]


class Sequence(BaseModel):
    sequence: str
    """Biological sequence (Nucleotide sequence)."""
    tag: str
    """Sequence description tag."""


def read_fasta(fasta_file: PathLike) -> List[Sequence]:
    """Reads fasta file into memory"""
    text = Path(fasta_file).read_text()
    text = re.sub(">$", "", text, flags=re.M)
    lines = [
        line.replace("\n", "")
        for seq in text.split(">")
        for line in seq.strip().split("\n", 1)
    ][1:]
    tags, seqs = lines[::2], lines[1::2]

    return [Sequence(sequence=seq, tag=tag) for seq, tag in zip(seqs, tags)]


def write_fasta(
    sequences: Union[Sequence, List[Sequence]], fasta_file: PathLike, mode: str = "w"
) -> None:
    seqs = [sequences] if isinstance(sequences, Sequence) else sequences
    with open(fasta_file, mode) as f:
        for seq in seqs:
            f.write(f">{seq.tag}\n{seq.sequence}\n")


def find_workseqs(in_files: List[Sequence]) -> List[Sequence]:

    num_nodes = int(os.environ.get("NRANKS", 1))
    num_gpus = num_nodes * 4
    gpu_rank = pmi_rank
    if num_gpus > 1:
        chunk_size = len(in_files) // num_gpus
        start_idx = gpu_rank * chunk_size
        end_idx = start_idx + chunk_size
        if gpu_rank + 1 == num_gpus:
            end_idx = len(in_files)

        print(
            f"GPU {gpu_rank} / {num_gpus} starting at {start_idx}, ending at {end_idx} ({len(in_files)=})"
        )
        node_data = in_files[start_idx:end_idx]
    else:
        node_data = in_files[:]

    return node_data


def run_esmfold(
    in_fasta_file: Path,
    out_dir: Path,
    executable_path: Path,
    cache_dir: str = "",
    test: bool = False,
) -> int:
    cache_command = f"--cache_dir {cache_dir}" if len(str(cache_dir)) != 0 else ""
    command = (
        f"python {str(executable_path)} "
        + f"--fasta {in_fasta_file} "
        + f"-o {out_dir} "
        + cache_command
    )
    if test:
        out_dir.mkdir(exist_ok=True, parents=True)
        with open(out_dir / "test_out.out", "w") as f:
            f.write("Out data")
        print("*" * 50, f"Testing, command: \n{command}")
        return 0

    res = subprocess.run(command.split())
    return res.returncode


def main(
    fasta: Path,
    out_dir: Path,
    executable_path: Path,
    glob_pattern: str,
    test: bool,
    cache_dir: Optional[str],
):
    out_dir.mkdir(exist_ok=True, parents=True)
    fasta_temp_dir = out_dir / "tmp_fasta"
    fasta_temp_dir.mkdir(exist_ok=True, parents=True)
    seqs = []
    if fasta.is_file():
        # Write each seq to a temp fasta file inside a dir
        for seq in read_fasta(fasta):
            fasta_temp_file = fasta_temp_dir / f"{seq.tag}.fasta"
            if not (out_dir / fasta_temp_file.stem).is_dir():
                seqs.append(seq)

    else:  # Is a directory of fasta files
        # Assuming just one seq per fasta file
        for file in fasta.glob(glob_pattern):
            seq = read_fasta(file)[0]  # Here is the one seq assumption
            fasta_temp_file = fasta_temp_dir / f"{seq.tag}.fasta"
            if not (out_dir / fasta_temp_file.stem).is_dir():
                seqs.append(seq)

    node_seqs = find_workseqs(seqs)

    for seq in node_seqs:
        fasta_temp_file = fasta_temp_dir / f"{seq.tag}.fasta"
        if not fasta_temp_file.is_file():
            write_fasta(seq, fasta_temp_file)

        file_out_dir = out_dir / fasta_temp_file.stem

        status_code = run_esmfold(
            fasta_temp_file, file_out_dir, executable_path, cache_dir, test
        )
        if status_code != 0:
            print(f"Error running {file}... continuing")

    print(f"Finished folding on gpu {pmi_rank} of rank {node_rank}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-f",
        "--fasta",
        type=Path,
        required=True,
        help="Directory of fastas or single fasta file",
    )
    parser.add_argument("-o", "--out_dir", type=Path, help="Path to output directory")
    parser.add_argument(
        "-g",
        "--glob_pattern",
        type=str,
        help="Glob pattern to search directory for fasta files (defaults to *.fasta)",
        default="*.fasta",
    )
    parser.add_argument(
        "--cache_dir",
        type=Path,
        help="If you have a custom torchhub path (would recomend setting one up, otherwise models go to your home directory)",
    )
    parser.add_argument(
        "--executable_path",
        type=Path,
        default=(Path(__file__).parent / "run_pretrained_esmfold.py").resolve(),
        help="Path to `run_pretrained_esmfold.py` (from this repo, it has been adapted to work with polaris env)",
    )
    parser.add_argument("-t", "--test", action="store_true")

    args = parser.parse_args()

    main(
        args.fasta,
        args.out_dir,
        args.executable_path,
        args.glob_pattern,
        args.test,
        args.cache_dir,
    )
