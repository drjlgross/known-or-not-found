python rnaseq_de.py --counts data/counts.csv --metadata data/metadata.csv --formula "~ condition" --contrast "condition,LPS,control" --backend pydeseq2 --output results/de/lps
