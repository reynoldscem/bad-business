from urllib.request import urlopen
from collections import Counter
from bs4 import BeautifulSoup
import numpy as np
import re

ADVENTURING_GEAR_URL = 'https://open5e.com/equipment/adventuring-gear.html'
TRADE_GOODS_URL = 'https://dnd5e.info/equipment/trade-goods'


class Item():
    @staticmethod
    def parse_weight(weight_string):
        if 'lb' not in weight_string:
            return 0.

        # Edge case of accidentally leading text before weight.
        weight_string = re.findall('\D*(\d+.*)', weight_string)[0]

        weight_string, *_ = weight_string.split()
        weight_string = weight_string.replace('½', '.5')

        fraction_match = re.match('(:?\d+)/(:?\d+)', weight_string)
        if fraction_match is None:
            weight = float(weight_string)
        else:
            numerator, denominator = map(int, fraction_match.groups())
            weight = numerator / denominator

        return weight

    @staticmethod
    def parse_cost(cost_string):
        cost_string = cost_string.replace(',', '')
        expression = re.compile('(:?\d+) (:?[csegp])p?.*')
        multipliers = {
            'c': 1,
            's': 10,
            'e': 50,
            'g': 100,
            'p': 1000
        }
        match = re.match(expression, cost_string)

        if match is None:
            raise Exception

        value_string, units_string = match.groups()
        value = int(value_string)

        copper_value = value * multipliers[units_string]

        return copper_value

    def __init__(self, name, cost, weight, scaling_factor=0.5):
        self.name = name
        self.cost = self.parse_cost(cost)
        self.weight = self.parse_weight(weight)

        self.cost_ratio = (self.cost) / (self.weight + scaling_factor)

    def __str__(self):
        return (
            'Name:\t{}\n\nCost:\t{}cp\n\n'
            'Weight:\t{}lbs.\n\nRatio:\t{:.4f}\n'
            ''.format(self.name, self.cost, self.weight, self.cost_ratio)
        )


def tag_text(tag):
    if tag.text == '\xa0':
        raise Exception
    else:
        return tag.text


def valid_entry(entry):
    num_fields = 3
    space_character = '\xa0'

    if len(entry) != num_fields:
        return False

    if entry[1].text == space_character:
        return False

    if entry[2].text == space_character:
        return False

    return True


def get_items():
    response = urlopen(ADVENTURING_GEAR_URL)
    data = response.read()
    soup = BeautifulSoup(data, 'html.parser')

    table_div = soup.find('div', {'id': 'adventuring-gear'})
    table_rows = table_div.table.tbody.find_all('tr')
    table_entries = [
        table_row.find_all('td')
        for table_row in table_rows
    ]

    table_entries = [
        list(map(tag_text, entry))
        for entry in table_entries
        if valid_entry(entry)
    ]

    items = [
        Item(name, cost, weight)
        for (name, cost, weight) in table_entries
    ]

    return items


def get_configuration(items, cost_budget_gp, weight_budget_lbs):
    ratios = [item.cost_ratio for item in items]
    ratio_total = sum(ratios)
    normalised_ratios = np.array(ratios) / ratio_total

    cost_budget = cost_budget_gp * 100
    weight_budget = weight_budget_lbs

    current_cost = 0
    current_weight = 0

    max_violations = 100

    probability_to_choose_uniformly = 0.95

    violations = 0
    selected_items = []
    while violations < max_violations:
        if np.random.uniform() < probability_to_choose_uniformly:
            next_item = np.random.choice(items)
        else:
            next_item = np.random.choice(items, p=normalised_ratios)

        if current_cost + next_item.cost > cost_budget:
            violations += 1
            continue
        if current_weight + next_item.weight > weight_budget:
            violations += 1
            continue

        violations = 0
        current_cost += next_item.cost
        current_weight += next_item.weight
        selected_items.append(next_item)

    return selected_items, current_cost, current_weight


def main():
    items = get_items()

    max_attempts = 250
    gold_budget = 250
    lbs_budget = 420 + 190

    candidate, candidate_cost, candidate_weight, candidate_fill_quotient = (
        None, None, None, None
    )
    for i in range(max_attempts):
        selected_items, cost, weight = get_configuration(
            items, gold_budget, lbs_budget
        )

        fill_quotient = weight / lbs_budget + cost / gold_budget
        if candidate is None:
            candidate = selected_items
            candidate_cost = cost
            candidate_weight = weight
            candidate_fill_quotient = fill_quotient
            continue

        if fill_quotient > candidate_fill_quotient:
            candidate = selected_items
            candidate_cost = cost
            candidate_weight = weight
            candidate_fill_quotient = fill_quotient

    selected_items, cost, weight = candidate, candidate_cost, candidate_weight

    print('Name | Cost | Weight | Count')
    print('--- | --- | --- | ---')

    def sorter(item_count_tuple):
        item, count = item_count_tuple
        return item.cost_ratio * count

    rows = sorted(
        Counter(selected_items).items(),
        key=sorter,
        reverse=True
    )
    for item, count in rows:
        print(
            '{} | {:.2f} gp | {:.2f} lbs. | {}'
            ''.format(item.name, item.cost / 100, item.weight, count)
        )

    print()
    print('Total weight:\t{:.2f} lbs.'.format(weight))
    print()
    print('Total cost:\t{:.2f} gp'.format(cost / 100))


if __name__ == '__main__':
    main()
