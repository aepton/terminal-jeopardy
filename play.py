import argparse
import os
import random
import re
import requests
import shutil
import textwrap

from bs4 import BeautifulSoup
from collections import OrderedDict
from fuzzywuzzy import fuzz
from pyfiglet import Figlet
from termcolor import colored
from terminaltables import SingleTable


class Game:
    def __init__(self, game_id):
        self.game_id = game_id

        self.current_round = 1

        self.players = {}
        self.rounds = {}

        self.update_terminal_width()
        self.display_intro()

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_board(self):
        self.clear_screen()

        current_round = self.rounds[self.current_round]
        board_data = [sorted(list(current_round.keys()))]

        values = set()
        for category in current_round:
            for val in current_round[category]:
                values.add(val)

        for val in sorted(values):
            row = []
            for key in sorted(current_round.keys()):
                if current_round[key].get(val, {}).get('active', False):
                    row.append('\n' + colored(f'${val:,}', 'yellow') + '\n')
                else:
                    row.append('\n\n')
            board_data.append(row)

        board = SingleTable(board_data, f'Round {self.current_round}')
        board.inner_row_border = True
        board.justify_columns = {k: 'center' for k, idx in enumerate(current_round.keys())}

        self.render_scores()

        print('\n')

        for line in str(board.table).splitlines():
            self.print_centered(line, width=board.table_width)

        self.load_clue(self.prompt_centered('Pick a clue'))

    def display_final_jeopardy(self):
        self.clear_screen()

        category = list(self.rounds[3].keys())[0]
        clue = self.rounds[3][category]

        self.print_centered('\n\n\n')
        self.print_centered('Final Jeopardy')
        self.print_centered('\n\n\n')

        self.render_scores()

        self.print_centered('\n\n\n')
        self.print_centered(category)

        self.print_centered('\n\n\n')

        input()
        wagers = {}
        for player in sorted(self.players):
            wagers[player] = self.prompt_centered(f'{self.players[player]["name"]}, your wager')

        self.print_centered('\n\n\n')
        self.print_centered(clue['text'])
        self.print_centered('\n\n\n\n\n\n')

        input()
        self.print_centered(f'What is {clue["answer"]}?')
        self.print_centered('\n\n\n')
        input()

        for player in sorted(self.players):
            correct = self.prompt_centered(f'Was {self.players[player]["name"]} correct? Y/N')
            if correct.lower() == 'y':
                self.players[player]['points'] += int(wagers[player])
            else:
                self.players[player]['points'] -= int(wagers[player])

        self.print_centered('\n\n\n\n\n\n')
        self.render_scores()
        self.print_centered('\n\n\n\n\n\n')

        input()

    def display_interstitial(self):
        self.clear_screen()

        self.print_centered('\n\n\n\n\n')

        self.print_centered(f'End of round {self.current_round}')

        self.print_centered('\n\n')

        self.render_scores()

        self.current_round += 1

        input()

        if self.current_round == 3:
            self.display_final_jeopardy()
        else:
            self.display_board()

    def display_intro(self):
        self.clear_screen()

        # Decent fonts: 'computer', 'banner', 'slant'
        f = Figlet(font='slant')

        print('\n\n\n\n\n\n\n\n\n\n\n\n')
        print(f.renderText('             Jeopardy!'))
        print('\n\n\n\n\n\n\n\n\n\n\n\n')

        self.populate_game()

    def load_clue(self, coords):
        if len(coords) != 2:
            self.display_board()

        c = coords[0].lower()
        r = coords[1].lower()
        if c not in ['a', 'b', 'c', 'd', 'e', 'f']:
            self.display_board()

        current_round = self.rounds[self.current_round]
        category = sorted(list(current_round.keys()))[ord(c) - ord('a')]

        all_values = set()
        for cat in current_round:
            for v in current_round[cat]:
                all_values.add(v)

        if (int(r) - 1) in all_values:
            val = sorted(all_values)[int(r) - 1]
        else:
            return self.display_board()
        
        if val not in current_round[category]:
            self.display_board()

        clue = current_round[category][val]

        if not clue['active']:
            self.display_board()

        players = []
        for idx in range(1, len(self.players.keys()) + 1):
            players.append(f'{self.players[idx]["name"]} ({idx})')

        self.clear_screen()

        print('\n\n\n\n\n\n\n\n\n\n\n\n')

        if clue['daily_double']:
            self.print_centered('Daily Double!')
            self.print_centered(category)
            self.print_centered('\n\n\n')

            player = ''
            while player not in self.players:
                player = self.prompt_centered(f'Who\'s guessing? {"; ".join(players)}', suffix='\n ')

                if player.isdigit():
                    player = int(player)
                elif player == '':
                    return

                if f' ({player})' not in ';'.join(players):
                    player = ''
                    continue
            
            self.print_centered('\n\n\n')
            wager = self.prompt_centered(
                f'How much are you wagering, {self.players[player]["name"]}?', suffix='\n '
            )

            self.print_centered(clue['text'], wrap=True)
            self.print_centered('\n\n')

            answer = clue['answer'].lower()
            guess = self.prompt_centered('What is ', suffix='\n ').lower()
            choice = ''
            print('\n\n')

            scores = [
                fuzz.ratio(guess, answer),
                fuzz.partial_ratio(guess, answer),
                fuzz.token_sort_ratio(guess, answer),
                fuzz.token_set_ratio(guess, answer)
            ]
            if min(scores) == 100:
                self.print_centered('Correct. The official answer is:')
                choice = 's'
            elif max(scores) >= 75 and min(scores) >= 50:
                self.print_centered('Likely correct')
            elif max(scores) >= 50 and min(scores) >= 35:
                self.print_centered('Not far off')
            else:
                self.print_centered('Unlikely to be right')

            input()
            print('\n\n')

            self.print_centered(textwrap.fill(f'What is {clue["answer"]}?'))

            correct = ''
            while correct.lower() not in ['y', 'n']:
                correct = self.prompt_centered(f'Was {self.players[player]["name"]} right? Y/N', suffix='\n ')

            if correct.lower() == 'y':
                self.players[player]['points'] += int(wager)
            else:
                self.players[player]['points'] -= int(wager)

            self.rounds[self.current_round][category][val]['active'] = False
        else:
            self.print_centered(f'{category} for ${val}')
            self.print_centered('\n\n')
            self.print_centered(clue['text'], wrap=True)
            self.print_centered('\n\n')

            choice = ''
            while choice.lower() not in ['g', 's', 'c']:
                choice = self.prompt_centered('(G)uess, (S)how, (C)ancel', suffix='\n ')

                if choice.lower() == 'g':
                    answer = clue['answer'].lower()
                    guess = self.prompt_centered('What is ', suffix='\n ').lower()
                    choice = ''
                    print('\n\n')

                    scores = [
                        fuzz.ratio(guess, answer),
                        fuzz.partial_ratio(guess, answer),
                        fuzz.token_sort_ratio(guess, answer),
                        fuzz.token_set_ratio(guess, answer)
                    ]
                    if min(scores) == 100:
                        self.print_centered('Correct. The official answer is:')
                        choice = 's'
                    elif max(scores) >= 75 and min(scores) >= 50:
                        self.print_centered('Likely correct')
                    elif max(scores) >= 50 and min(scores) >= 35:
                        self.print_centered('Not far off')
                    else:
                        self.print_centered('Unlikely to be right')

                if choice.lower() == 's':
                    self.print_centered(textwrap.fill(f'What is {clue["answer"]}?'))

                    self.record_guess_result(val, players)

                    self.rounds[self.current_round][category][val]['active'] = False

        active_clues = False
        for category in self.rounds[self.current_round]:
            for val in self.rounds[self.current_round][category]:
                if self.rounds[self.current_round][category].get(val, {}).get('active', False):
                    active_clues = True

        if active_clues:
            self.display_board()
        else:
            self.display_interstitial()

    def parse_round(self, rnd):
        round_data = {}

        round_names = {
            1: 'jeopardy_round',
            2: 'double_jeopardy_round',
            3: 'final_jeopardy_round'
        }
        round_id = round_names[rnd]

        r = self.soup.find(id=round_id)

        # The game may not have all the rounds
        if not r:
            return False

        # The list of categories for this round
        categories = [c.get_text() for c in r.find_all("td", class_="category_name")]

        for category in categories:
            round_data[category] = OrderedDict()

        if rnd == 3:
            for c in r.find_all("td", class_="category"):
                for a in r.find_all("td", class_="clue"):
                    text = a.find('td', class_='clue_text').get_text()
                    answer = BeautifulSoup(
                        c.find('div', onmouseover=True).get('onmouseover'), 'lxml'
                    )
                    answer = answer.find('em').get_text()
                    round_data[categories[0]] = {
                        'text': text,
                        'answer': answer,
                        'active': True
                    }
        else:
            # The x_coord determines which category a clue is in because the categories come before
            # the clues, we will have to match them up with the clues later on.
            x = 0
            for a in r.find_all("td", class_="clue"):
                is_missing = True if not a.get_text().strip() else False
                if not is_missing:
                    value = int(
                        a.find(
                            'td',
                            class_=re.compile('clue_value')
                        ).get_text().lstrip('D: $').replace(',', '')
                    )
                    text = a.find('td', class_='clue_text').get_text()
                    answer = BeautifulSoup(
                        a.find('div', onmouseover=True).get('onmouseover'), 'lxml'
                    )
                    answer = answer.find('em', class_='correct_response').get_text()
                    is_dd = a.find('td', class_='clue_value_daily_double') is not None
                    round_data[categories[x]][value] = {
                        'text': text,
                        'answer': answer,
                        'active': True,
                        'daily_double': is_dd
                    }

                x = 0 if x == 5 else x + 1

        if rnd < 3:
            for category in round_data:
                dd_vals = []
                for val in round_data[category].keys():
                    if round_data[category][val]['daily_double']:
                        dd_vals.append(val)

                for val in dd_vals:
                    found_missing = False
                    for other_category in round_data:
                        if other_category == category:
                            continue
                        for other_val in round_data[other_category]:
                            if other_val not in round_data[category]:
                                round_data[category][other_val] = round_data[category][val]
                                del round_data[category][val]
                                found_missing = True
                                break
                        if found_missing:
                            break

        return round_data

    def populate_game(self):
        """
        season = self.prompt_centered('Enter season number from 1 to 37, leave blank for random')
        if season = '':
            season = random.randint(1, 37)
        else:
            season = int(season)

        season_response = requests.get(f'https://www.j-archive.com/showseason.php?season={season}')
        season_soup = BeautifulSoup(season_response.text, features='lxml')
        """
        response = requests.get(f'https://www.j-archive.com/showgame.php?game_id={self.game_id}')
        soup = BeautifulSoup(response.text, features='lxml')

        self.air_date = soup.title.get_text().split()[-1]
        self.soup = soup

        for rnd in [1, 2, 3]:
            self.rounds[rnd] = self.parse_round(rnd)

        self.print_centered('\n\n')
        self.print_centered(f'Episode air date: {self.air_date}')

        self.setup_game()
    
    def print_centered(self, text, width=None, wrap=False):
        self.update_terminal_width()

        if wrap:
            lines = textwrap.wrap(text)
        else:
            lines = [text]

        for line in lines:
            line_width = width
            if line_width is None:
                line_width = len(line)

            padding = (self.terminal_width - line_width)/ 2.
            padding_str = ' ' * int(padding)

            print(f'{padding_str}{line}')

    def prompt_centered(self, prompt, suffix=':\n'):
        self.update_terminal_width()
        return input(f'{prompt}{suffix}'.center(self.terminal_width))

    def record_guess_result(self, val, players):
        print('\n\n')

        player = ''
        while player not in self.players:
            player = self.prompt_centered(f'Who guessed? {"; ".join(players)}', suffix='\n ')

            if player.isdigit():
                player = int(player)
            elif player == '':
                return

            if f' ({player})' not in ';'.join(players):
                player = ''
                continue

        correct = ''
        while correct.lower() not in ['y', 'n']:
            correct = self.prompt_centered('Were they right? Y/N', suffix='\n ')

        if correct.lower() == 'y':
            self.players[player]['points'] += val
        else:
            self.players[player]['points'] -= val

        remaining_players = list(filter(lambda p: not p.endswith(f' ({player})'), players))
        if len(remaining_players):
            self.record_guess_result(val, remaining_players)

    def render_scores(self):
        player_names = []
        player_scores = []
        for idx in range(1, len(self.players.keys()) + 1):
            player_names.append(self.players[idx]['name'])
            player_scores.append(
                '\n' +
                colored(f'${self.players[idx]["points"]:,}', 'yellow') +
                '\n'
            )

        score_data = [player_names, player_scores]
        scores = SingleTable(score_data)
        scores.justify_columns = {k: 'center' for k, idx in enumerate(self.players.keys())}

        for line in str(scores.table).splitlines():
            self.print_centered(line, width=scores.table_width)

    def setup_game(self):
        current_player = 1
        name = 'default'
        input()
        while name:
            name = self.prompt_centered(f'Player {current_player}', suffix='\n ')
            if name:
                self.players[current_player] = {'name': name, 'points': 0}
                current_player += 1

        if self.current_round == 3:
            self.display_final_jeopardy()
        else:
            self.display_board()

    def update_terminal_width(self):
        self.terminal_width = shutil.get_terminal_size().columns


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Let\'s play Jeopardy!')
    parser.add_argument('game_id', type=str, help='id of the game to play')
    args = parser.parse_args()

    game = Game(args.game_id)
