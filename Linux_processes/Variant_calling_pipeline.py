import subprocess
import os


class Variant_calling_pipeline:

    def __init__(
        self,
        reference_genome,
        fastq1,
        fastq2,
        output_dir
    ):

        self.reference_genome = reference_genome
        self.fastq1 = fastq1
        self.fastq2 = fastq2
        self.output_dir = output_dir

        self.fastp = "biocontainers/fastp:v0.19.6dfsg-1-deb_cv1"
        self.bwa = "quay.io/biocontainers/bwa:0.7.19--h577a1d6_1"
        self.samtools = "quay.io/biocontainers/samtools:1.21--h96c455f_1"
        self.gatk = "broadinstitute/gatk:latest"

        # Mount current project directory
        self.project_root = os.path.abspath(
            os.path.join(output_dir, "..", "..")
        )

    # --------------------------------------------------

    def run_command(self, cmd):

        print("\n==============================")
        print(cmd)
        print("==============================\n")

        result = subprocess.run(
            ["bash", "-c", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:
            raise Exception(result.stderr)

        return result.stdout.strip()

    # --------------------------------------------------

    def trimming(self):

        cmd = f"""
        docker run --rm \
        -v {self.project_root}:{self.project_root} \
        -w {self.project_root} \
        {self.fastp} \
        fastp \
        -i "{self.fastq1}" \
        -I "{self.fastq2}" \
        -o "{self.output_dir}/trimmed_R1.fastq" \
        -O "{self.output_dir}/trimmed_R2.fastq"
        """

        return self.run_command(cmd)

    # --------------------------------------------------

    def alignment(self):

        cmd = f"""
        docker run --rm \
        -v {self.project_root}:{self.project_root} \
        -w {self.project_root} \
        {self.bwa} \
        bwa mem \
        -t 4 \
        -R '@RG\\tID:sample1\\tSM:sample1\\tPL:ILLUMINA' \
        "{self.reference_genome}" \
        "{self.output_dir}/trimmed_R1.fastq" \
        "{self.output_dir}/trimmed_R2.fastq" \
        > "{self.output_dir}/aligned.sam"
        """

        return self.run_command(cmd)

    # --------------------------------------------------

    def sam_to_bam(self):

        cmd = f"""
        docker run --rm \
        -v {self.project_root}:{self.project_root} \
        -w {self.project_root} \
        {self.samtools} \
        samtools view \
        -bS \
        "{self.output_dir}/aligned.sam" \
        -o "{self.output_dir}/aligned.bam"
        """

        return self.run_command(cmd)

    # --------------------------------------------------

    def sort_bam(self):

        cmd = f"""
        docker run --rm \
        -v {self.project_root}:{self.project_root} \
        -w {self.project_root} \
        {self.samtools} \
        samtools sort \
        "{self.output_dir}/aligned.bam" \
        -o "{self.output_dir}/aligned_sorted.bam"
        """

        return self.run_command(cmd)
    


        # --------------------------------------------------
    # Mark Duplicates
    # --------------------------------------------------

    def mark_duplicates(self):

        cmd = f"""
        docker run --rm \
        -v {self.project_root}:{self.project_root} \
        -w {self.project_root} \
        {self.gatk} \
        gatk MarkDuplicates \
        -I "{self.output_dir}/aligned_sorted.bam" \
        -O "{self.output_dir}/aligned_marked.bam" \
        -M "{self.output_dir}/metrics.txt"
        """

        return self.run_command(cmd)

    # --------------------------------------------------
    # Index BAM
    # --------------------------------------------------

    def index_bam(self):

        cmd = f"""
        docker run --rm \
        -v {self.project_root}:{self.project_root} \
        -w {self.project_root} \
        {self.samtools} \
        samtools index \
        "{self.output_dir}/aligned_marked.bam"
        """

        return self.run_command(cmd)

    # --------------------------------------------------
    # Variant Calling
    # --------------------------------------------------

    def variant_calling(self):

        cmd = f"""
        docker run --rm \
        -v {self.project_root}:{self.project_root} \
        -w {self.project_root} \
        {self.gatk} \
        gatk HaplotypeCaller \
        -R "{self.reference_genome}" \
        -I "{self.output_dir}/aligned_marked.bam" \
        -O "{self.output_dir}/variants.vcf"
        """

        return self.run_command(cmd)

    # --------------------------------------------------
    # Complete Pipeline
    # --------------------------------------------------

    def run_pipeline(self):

        print("\n===================================")
        print("Starting Variant Calling Pipeline")
        print("===================================\n")

        print("Step 1/7 : Quality Control & Trimming")
        self.trimming()

        print("✓ Trimming Completed\n")

        print("Step 2/7 : Read Alignment")
        self.alignment()

        print("✓ Alignment Completed\n")

        print("Step 3/7 : SAM → BAM Conversion")
        self.sam_to_bam()

        print("✓ BAM Conversion Completed\n")

        print("Step 4/7 : Sorting BAM")
        self.sort_bam()

        print("✓ BAM Sorting Completed\n")

        print("Step 5/7 : Marking Duplicates")
        self.mark_duplicates()

        print("✓ Duplicate Marking Completed\n")

        print("Step 6/7 : BAM Indexing")
        self.index_bam()

        print("✓ BAM Index Created\n")

        print("Step 7/7 : Variant Calling")
        self.variant_calling()

        print("✓ Variant Calling Completed\n")

        print("===================================")
        print("Pipeline Finished Successfully")
        print("===================================\n")

        print(f"Results Directory : {self.output_dir}")
        print(f"VCF File          : {self.output_dir}/variants.vcf")
        print(f"BAM File          : {self.output_dir}/aligned_marked.bam")
        print(f"Metrics File      : {self.output_dir}/metrics.txt")

        return {
            "vcf": f"{self.output_dir}/variants.vcf",
            "bam": f"{self.output_dir}/aligned_marked.bam",
            "metrics": f"{self.output_dir}/metrics.txt"
        }