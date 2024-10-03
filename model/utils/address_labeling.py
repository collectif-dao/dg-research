import csv


def assign_labels_by_funds_threshold(funds_threshold: int, main_label: str, counter_label: str):
    labeled_addresses: dict[str, str] = dict()

    with open("data/stETH_token_distribution.csv", mode="r") as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=",")
        line_count = 0

        for row in csv_reader:
            if line_count == 0:
                line_count += 1
                continue

            total_funds = int(float(row["total"]))

            if total_funds >= funds_threshold:
                labeled_addresses[row["address"]] = main_label
            else:
                labeled_addresses[row["address"]] = counter_label

    return labeled_addresses
