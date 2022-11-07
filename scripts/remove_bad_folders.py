from argparse import ArgumentParser
from pathlib import Path
import subprocess


def main(input_dir: Path):
    to_delete = []
    for dir in input_dir.glob("*"):
        num_out_files = len(list(dir.glob("*.out")))
        num_pdb_files = len(list(dir.glob("*.pdb")))
        num_fasta_files = len(list(dir.glob("*.fasta")))
        if num_out_files > 0 and num_pdb_files == 0 and num_fasta_files == 0:
            to_delete.append(dir)

    for dir in to_delete:
        print(subprocess.run(["rm", "-rf", str(dir)]))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-i", "--input_dir", type=Path, help="Input direcotry to cleanup"
    )

    args = parser.parse_args()
    main(args.input_dir)
