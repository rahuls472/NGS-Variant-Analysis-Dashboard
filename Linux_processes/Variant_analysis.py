import subprocess
import os

class VariantAnalysis:

    def __init__(self, file_path):
        self.file_path = file_path
        self.project_root = os.path.abspath(
            os.path.join(self.file_path, "..", "..")
        )
        self.bcftools = "staphb/bcftools:latest"

    def _docker_prefix(self):
        return (
            f"docker run --rm "
            f"-v {self.project_root}:{self.project_root} "
            f"-w {self.project_root} "
            f"{self.bcftools} "
        )

    def run_command(self, cmd):
        result = subprocess.run(
            ["bash", "-c", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.stderr:
            print("ERROR:", result.stderr)
        return result.stdout.strip()

    def get_total_variants(self):
        cmd = f'{self._docker_prefix()} bcftools view -H "{self.file_path}" | wc -l'
        return self.run_command(cmd)

    def get_snp_count(self):
        cmd = f'{self._docker_prefix()} bcftools view -H -v snps "{self.file_path}" | wc -l'
        return self.run_command(cmd)

    def get_indel_count(self):
        cmd = f'{self._docker_prefix()} bcftools view -H -v indels "{self.file_path}" | wc -l'
        return self.run_command(cmd)

    def get_avg_qual(self):

        quals = self.get_qual_scores()

        if len(quals) == 0:
            return 0

        return round(sum(quals) / len(quals), 2)

    def get_avg_depth(self):

        depths = self.get_depth_values()

        if len(depths) == 0:
            return 0

        return round(sum(depths) / len(depths), 2)

    def get_variant_table(self, page=1, per_page=50):
        start = (page - 1) * per_page + 1
        end = start + per_page - 1
        cmd = (
            f'{self._docker_prefix()} bcftools query '
            f'-f \'%CHROM\\t%POS\\t%REF\\t%ALT\\t%QUAL\\t%INFO/DP\\n\' "{self.file_path}" | '
            f"sed -n '{start},{end}p'"
        )
        output = self.run_command(cmd)
        variants = []
        for line in output.splitlines():
            cols = line.split('\t')
            variants.append({
                "chrom": cols[0],
                "pos":   cols[1],
                "ref":   cols[2],
                "alt":   cols[3],
                "qual":  cols[4],
                "dp":    cols[5]
            })
        return variants

    def get_qual_scores(self):
        cmd = f'{self._docker_prefix()} bcftools query -f \'%QUAL\\n\' "{self.file_path}"'
        output = self.run_command(cmd)
        return [float(q) for q in output.splitlines() if q != "."]

    def get_pass_variants(self):
        cmd = f'{self._docker_prefix()} bcftools view -f PASS -H "{self.file_path}" | wc -l'
        return self.run_command(cmd)

    def get_filtered_variants(self):
        cmd = f'{self._docker_prefix()} bcftools view -e \'FILTER="PASS"\' -H "{self.file_path}" | wc -l'
        return self.run_command(cmd)

    def get_filter_status(self):
        cmd = f'{self._docker_prefix()} bcftools query -f \'%FILTER\\n\' "{self.file_path}" | sort | uniq -c'
        output = self.run_command(cmd)
        result = {}
        for line in output.splitlines():
            parts = line.strip().split(maxsplit=1)
            count = int(parts[0])
            status = parts[1] if len(parts) > 1 else "Unfiltered"
            if status == ".":
                status = "Unfiltered"
            result[status] = count
        return result

    def get_low_depth_count(self, threshold=10):
        cmd = f'{self._docker_prefix()} bcftools query -f \'%INFO/DP\\n\' "{self.file_path}"'
        output = self.run_command(cmd)
        return sum(1 for dp in output.splitlines() if dp.isdigit() and int(dp) < threshold)

    def get_titv_ratio(self):
        cmd = f'{self._docker_prefix()} bcftools query -f \'%REF\\t%ALT\\n\' "{self.file_path}"'
        output = self.run_command(cmd)
        transitions = {('A','G'), ('G','A'), ('C','T'), ('T','C')}
        ti = tv = 0
        for line in output.splitlines():
            parts = line.split('\t')
            if len(parts) != 2:
                continue
            ref, alt = parts
            if len(ref) != 1 or len(alt) != 1:
                continue
            if (ref, alt) in transitions:
                ti += 1
            else:
                tv += 1
        return {
            "transitions":   ti,
            "transversions": tv,
            "ratio":         round(ti / tv, 2) if tv > 0 else 0
        }

    def get_depth_values(self):
        cmd = f'{self._docker_prefix()} bcftools query -f \'%INFO/DP\\n\' "{self.file_path}"'
        output = self.run_command(cmd)
        return [int(dp) for dp in output.splitlines() if dp.isdigit()]