from boto3 import resource, client
from boto3.dynamodb.conditions import Key, Attr
from copy import deepcopy
from datetime import datetime
from pytz import timezone
from decimal import Decimal
from scipy.stats import norm

db = resource('dynamodb')

table = db.Table('nfl_schedule')
odds_table = db.Table('nfl_sport_events')
engine_table = db.Table('decision-engine-nfl')
betrics_table = db.Table('nfl-standard-betrics')
stats_table = db.Table('nfl_season_stats')
book_table = db.Table('book_subscription')

client = client('lambda')

LOGO_URL = 'https://bucket212121.s3.us-east-2.amazonaws.com/nfl-logos/'
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

# Projection Standard Values
spread_SD = Decimal(-3.0)
total_SD = Decimal(3.0)
perc_per_point = Decimal(2.66)
prob_SD = Decimal(10.0)


def getAllData(q1):
    try:
        response = table.get_item(
            Key={'title': q1}
        )
        items = response.get('Item')
        if items:
            return items.get('games')
        else:
            return None
    except:
        return

    # this function fetch all week from db and send to front-end


def getAllWeek():
    current_week = None

    dates = """9/7/2021	9/13/2021
    9/14/2021	9/20/2021
    9/21/2021	9/27/2021
    9/28/2021	10/4/2021
    10/5/2021	10/11/2021
    10/12/2021	10/18/2021
    10/19/2021	10/25/2021
    10/26/2021	11/1/2021
    11/2/2021	11/8/2021
    11/9/2021	11/15/2021
    11/16/2021	11/22/2021
    11/23/2021	11/29/2021
    11/30/2021	12/6/2021
    12/7/2021	12/13/2021
    12/14/2021	12/20/2021
    12/21/2021	12/27/2021
    12/28/2021	1/3/2022
    1/4/2022	1/9/2022
    1/10/2022	1/17/2022
    1/18/2022	1/23/2022
    1/24/2022	1/30/2022
    1/31/2022	2/13/2022"""

    t = [tuple(i.replace('\t', ',').split(',')) for i in dates.split('\n')]

    currentdate = datetime.now(tz=timezone("US/pacific")).strftime('%Y-%m-%d')
    cy, cm, cd = list(map(int, currentdate.split('-')))
    current_date = datetime(cy, cm, cd)

    for k, v in enumerate(t):
        d1, d2 = v
        m, d, y = list(map(int, d1.split('/')))
        m2, d2, y2 = list(map(int, d2.split('/')))

        date1 = datetime(y, m, d)
        date2 = datetime(y2, m2, d2)
        if date2 >= current_date:
            if k + 1 == 19:
                current_week = 'WC'
                break
            elif k + 1 == 20:
                current_week = 'DV'
                break
            elif k + 1 == 21:
                current_week = 'CF'
                break
            elif k + 1 == 22:
                current_week = 'SB'
                break
            else:
                current_week = int(k + 1)
                break

    response = table.scan()

    if len(response.get("Items")) == 0:
        return "no data found"
    else:
        weeks = []
        pre_weeks = []

        for i in response.get("Items"):
            # print(i.get("title"))
            try:
                val = int(i.get('title'))
                weeks.append({'label': f"Week {val}", "value": val})

            except ValueError:
                pre_weeks.append({'label': f"Week {i.get('title')}", "value": i.get("title")})

        weeks.sort(key=lambda k: k['value'])
        pre_weeks.sort(key=lambda k: k['value'])

        # print(pre_weeks + weeks)

        return {
            "dropdown": pre_weeks + weeks,
            "current_week": {
                "label": f"week {current_week}",
                "value": current_week
            }
        }


# Function to get sr_id from uuid
def get_sr_id(match):
    response = odds_table.query(
        IndexName='uuids-index',
        KeyConditionExpression=Key('uuids').eq(match)
    )
    data = response.get('Items')
    try:
        return data[0].get('id')
    except:
        return None


# Function to call retrive odds from DB and append to Schedule data
def getOdds(match, book):
    '''
    #Original function - obsoleted by J.T. on 7/19/21
    if book:
        inputForInvoker = {
            'match': match,
            'book': book
        }
        raw_data = client.invoke(
            FunctionName='arn:aws:lambda:us-east-2:562275630075:function:nfl-get-odds',
            InvocationType='RequestResponse',
            Payload = json.dumps(inputForInvoker)
        )
        if raw_data.get('Payload'):
            markets = json.loads(raw_data['Payload'].read())
        else:
            markets = {}
    '''

    '''
    #Iterating Through NFL Markets Table
    markets_table = db.Table('nfl_markets')

    response = markets_table.get_item(Key={'sr_id':match})

    if response.get('Item', False):
        market_list = response['Item'].get('markets',[])
        for item in market_list:
            if item.get('book') == book: market_response = item
    '''

    # Leveraging NFL Markets-By-Book Table
    markets_table = db.Table('nfl-markets-by-book')

    response = markets_table.get_item(Key={
        'sr_id': match,
        'book_id': book
    })

    if response.get('Item', False):
        market_response = response['Item'].get('data')

    return market_response


def get_bet_percentage(match):
    response = odds_table.get_item(Key={'id': match})
    data = response.get('Item', False)
    perc_dict = {}
    if data:
        consensus = data.get('consensus', {})
        percentages = consensus.get('bet_percentage_outcomes', [])
        for market in percentages:
            perc = {}
            for outcome in market.get('outcomes', []):
                if outcome.get('type') == 'home' or outcome.get('type') == 'over':
                    home_perc = deepcopy(outcome)
                    perc.update({
                        outcome['type']: str(home_perc.get('percentage', "False")) + "%"
                    })
                if outcome.get('type') == 'away' or outcome.get('type') == 'under':
                    away_perc = deepcopy(outcome)
                    perc.update({
                        outcome['type']: str(away_perc.get('percentage', "False")) + "%"
                    })

            perc_dict.update({market.get('name', "none"): perc})

    if 'moneyline' not in perc_dict:
        perc_dict.update({'moneyline': {'home': 'OFF', 'away': 'OFF'}})

    if "spread" not in perc_dict:
        perc_dict.update({'spread': {'home': 'OFF', 'away': 'OFF'}})

    if "total" not in perc_dict:
        perc_dict.update({'total': {'over': 'OFF', 'under': 'OFF'}})

    if not perc_dict:
        perc_dict.update({
            'moneyline': {
                'home': '0%',
                'away': '0%'
            },
            'spread': {
                'home': '0%',
                'away': '0%'
            },
            'total': {
                'home': '0%',
                'away': '0%'
            },
        })

    return perc_dict


'''
#This function will be used to bring in live scores when available
def get_scores(id):
     game_table = db.Table('nba-game-summary')
     response=game_table.query(
          KeyConditionExpression=Key('sr_id').eq(id)
     )
     items = response['Items']
     try:
          return items[0]['data']
     except:
          return {}
'''

'''
#This function may be used later to bring in bet percentage
def get_perc(id):
     table = db.Table('nba-bet-percentage')
     response=table.query(KeyConditionExpression=Key('sr_id').eq(id))
     items = response['Items']
     try:
          data = items[0]
     except:
          data = {}

     return data
'''


def already_bet_placed_data(data, book_id, user):
    queue_table = db.Table('bet_queue')

    response = queue_table.query(
        IndexName='username-index',
        KeyConditionExpression=Key('username').eq(user)
    )

    bet_queue_data = response.get('Items', [])
    # pprint(bet_queue_data)

    ####################################
    bet_data = {book_id: {}}
    for x in bet_queue_data:

        if book_id != x['sr:book:id']:
            continue

        match_id = x['sr:match:id']

        if bet_data.get(book_id).get(match_id, False):
            bet_data[book_id][match_id].append(x)
        else:
            bet_data[book_id][match_id] = [x]

    #####################################
    updated_data = []

    for item in data:
        match = item.get('sr:match:id')

        check_sum = {
            "home_spread": False,
            "home_moneyline": False,
            "home_total": False,

            "away_spread": False,
            "away_moneyline": False,
            "away_total": False,
        }

        # for i in bet_placed_data:
        for i in bet_data.get(book_id).get(match, []):

            if i.get('bet_side') == "home":
                if i.get('bet_type') == "spread":
                    check_sum.update({'home_spread': True})
                elif i.get('bet_type') == "moneyline":
                    check_sum.update({'home_moneyline': True})

            elif i.get('bet_side') == "away":
                if i.get('bet_type') == "spread":

                    check_sum.update({'away_spread': True})
                elif i.get('bet_type') == "moneyline":

                    check_sum.update({'away_moneyline': True})


            elif i.get('bet_side') == "over":
                check_sum.update({'away_total': True})

            elif i.get('bet_side') == "under":
                check_sum.update({'home_total': True})

        item.update({"bet_placed": check_sum})
        updated_data.append(item)

    return updated_data


def get_dip_projections(data, week, dip):
    game_id = data.get('sr:match:id', 'none')
    home_team = data.get('home').get('sr_id', 'none')
    away_team = data.get('away').get('sr_id', 'none')

    book_spread = data.get('markets').get('spread').get('current').get('home_spread')
    book_total = data.get('markets').get('total').get('current').get('total')
    book_perc = data.get('markets').get('moneyline').get('current').get('home_imp')

    if dip == 'pff' or dip == 'rotowire' or dip == 'madden':
        if dip == 'pff':
            dip_table = db.Table('nfl-pff-projections')
            proj_key = 'projection'
            proj_title = 'PFF Team Grade Projection'
            betric = 'pff_team_grades'
        elif dip == 'rotowire':
            dip_table = db.Table('nfl_rotowire_projections_team')
            proj_key = 'projected'
            proj_title = 'Rotowire Team Projection'
            betric = 'rotowire_team_projection'
        elif dip == 'madden':
            dip_table = db.Table('nfl-madden-projections')
            proj_key = 'projection'
            proj_title = 'Madden Team Rating Projection'
            betric = 'madden_rating'

        home_response = dip_table.get_item(Key={
            'id': home_team,
            'week': week
        })
        home_data = home_response.get('Item', {})
        home_score = Decimal(home_data.get(proj_key, 0.0))

        away_response = dip_table.get_item(Key={
            'id': away_team,
            'week': week
        })
        away_data = away_response.get('Item', {})
        away_score = Decimal(away_data.get(proj_key, 0.0))

    elif dip == 'vsin-BR' or dip == 'vsin-est':
        dip_table = db.Table('nfl-vsin-projections')
        response = dip_table.get_item(Key={'sr_id': game_id})
        vsin_data = response.get('Item', {}).get('ratings', {})
        if dip == 'vsin-BR':
            betric = 'vsin_bettor_rating'
            proj_title = 'VSiN Bettor Rating'
            home_score = Decimal(vsin_data.get('BR_HomeScore', 0.0))
            away_score = Decimal(vsin_data.get('BR_RoadScore', 0.0))
        elif dip == 'vsin-est':
            betric = 'vsin_effective_strength'
            proj_title = 'VSiN Effective Strength'
            home_score = Decimal(vsin_data.get('est_homescore', 0.0))
            away_score = Decimal(vsin_data.get('est_roadscore', 0.0))

    elif dip == 'odds-shark':
        betric = 'odds_shark_computer_projection'
        proj_title = 'Odds Shark Computer Projections'
        dip_table = db.Table('nfl-odds-shark')
        response = dip_table.get_item(Key={'sr_id': game_id})
        odds_shark_data = response.get('Item', {})
        home_score = Decimal(odds_shark_data.get('home_score', 0.0))
        away_score = Decimal(odds_shark_data.get('away_score', 0.0))

        # Spread
    spread_raw = away_score - home_score
    if spread_raw < 0:
        home_spread = str(spread_raw)
        away_spread = '+' + str(-spread_raw)
    elif spread_raw > 0:
        home_spread = '+' + str(spread_raw)
        away_spread = str(-spread_raw)
    else:
        home_spread = str(spread_raw)
        away_spread = str(spread_raw)
    if book_spread != 'OFF':
        book_spread = book_spread.replace('+', "")
        spread_diff_ans = spread_raw - Decimal(book_spread)
        spread_diff = -spread_diff_ans
        spread_perc = max(min(spread_diff / spread_SD, Decimal(1.0)), Decimal(-1.0))
    else:
        spread_perc = Decimal(0.0)

    # Total
    total_raw = away_score + home_score
    over_total = 'o' + str(total_raw)
    under_total = 'u' + str(total_raw)
    if book_total != 'OFF':
        total_diff = (total_raw - Decimal(book_total))
        total_perc = max(min(total_diff / total_SD, Decimal(1.0)), Decimal(-1.0))
    else:
        total_perc = Decimal(0.0)

    # Moneyline (Implied Probability)
    home_prob = Decimal(50.0) - perc_per_point * spread_raw
    away_prob = Decimal(100.0) - home_prob
    home_prob_str = str(round(home_prob, 1)) + '%'
    away_prob_str = str(round(away_prob, 1)) + '%'
    if book_perc != 'OFF':
        book_perc = book_perc.replace('%', "")
        prob_diff = - (home_prob - Decimal(book_perc))
        prob_perc = max(min(prob_diff / prob_SD, Decimal(1.0)), Decimal(-1.0))
    else:
        prob_perc = Decimal(0.0)

    proj_response = {
        'dip': dip,
        'betric': betric,
        'title': proj_title,
        'spread': spread_raw,
        'home_spread': home_spread,
        'away_spread': away_spread,
        'spread_perc': round(spread_perc, 2),
        'total': total_raw,
        'over_total': over_total,
        'under_total': under_total,
        'total_perc': round(total_perc, 2),
        'home_win': home_prob_str,
        'away_win': away_prob_str,
        'prob_perc': round(prob_perc, 2)
    }

    return proj_response


def get_projections(data, week):
    dip_list = ['pff', 'rotowire', 'vsin-BR', 'vsin-est', 'madden', 'odds-shark']
    proj_list = []
    for dip_name in dip_list:
        proj_list.append(get_dip_projections(data, week, dip_name))

    return proj_list


def matchup_view(user, book_id, match_data):
    bet_table = db.Table('bet_tracking')
    event_table = db.Table('wager_event')

    response = bet_table.query(
        IndexName='username-index',
        KeyConditionExpression=Key('username').eq(user)
    )

    data = response.get('Items', [])

    match_up_data = {}

    for wager in data:
        events_list = wager.get('events', [])

        for event_id in events_list:

            event_key = {
                'bet_id': event_id,
                'username': user
            }

            event_response = event_table.get_item(Key=event_key)
            event_data = event_response.get('Item', {})

            match_id = event_data.get('sr:match:id', 'sr')

            if match_up_data.get(match_id, False):
                match_up_data[match_id].append(event_data)
            else:
                match_up_data[match_id] = [event_data]

    updated_data = []

    for item in match_data:
        match_id = item.get('sr:match:id')
        item.update({"matchup_view": match_up_data.get(match_id)})

        updated_data.append(item)

    return updated_data


def am_from_prob(prob):
    dec = 1.0 / prob
    if dec >= 2.0:
        am = (dec - 1.0) * 100.0
        am_str = f"+{int(round(am, 0))}"
    else:
        am = -100.0 / (dec - 1.0)
        am_str = str(int(round(am, 0)))

    return am_str


def prob_from_am(am):
    if am >= 100:
        prob = 100.0 / (am + 100.0)
    else:
        prob = -am / (-am + 100.0)

    return prob


def engine_calcs(user_id, game):
    try:
        response = engine_table.query(
            IndexName='user_id-index',
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        data = response.get('Items', False)

        game_id = game.get('sr_id', False)
        response = betrics_table.get_item(Key={'id': game_id})
        game_data = response.get('Item', False)

        engine_response = {}
        # requests.post('https://webhook.site/8c7e28a5-c43d-4ee5-b657-12afcdafddb8', data=dumps({"line" : 563}))
        if data and game_data:
            for item in data:
                if item.get('engine_status', False):
                    engine_weights = item.get('weights')

                    # 0 - win prob
            # 1 - spread
            # 2 - total
            weights = [0.0, 0.0, 0.0]
            values = [0.0, 0.0, 0.0]
            # requests.post('https://webhook.site/8c7e28a5-c43d-4ee5-b657-12afcdafddb8', data=dumps({"line" : 574}))
            for weight_data in engine_weights:
                # weight_raw = engine_weights[betric]
                betric = weight_data["market_place_name"]
                # print(betric)
                weight_raw = weight_data["value"]
                try:
                    betric_weight = float(weight_raw.replace("%", "")) / 100.0
                except:
                    betric_weight = 0.0
                if weight_data.get("active") and game_data.get(betric, False):
                    # Probability
                    weights[0] += betric_weight
                    values[0] += betric_weight * float(game_data.get(betric, {}).get('prob', 0.0))

                    # Spread
                    weights[1] += betric_weight
                    values[1] += betric_weight * float(game_data.get(betric, {}).get('spread', 0.0))

                    # Total
                    weights[2] += betric_weight
                    values[2] += betric_weight * float(game_data.get(betric, {}).get('total', 0.0))

                    # if game_id == 'sr:match:27299744': #print(game_id, betric, betric_weight, weights, values)

            # print(" pass in 593 ")
            if weights[0] > 0:
                home_prob = round(values[0] / weights[0], 4)
                away_prob = round(1.0 - home_prob, 4)
            else:
                home_prob = 'OFF'
                away_prob = 'OFF'

            if weights[1] > 0:
                home_spread = round(values[1] / weights[1], 1)
                away_spread = round(-home_spread, 1)
            else:
                home_spread = 'OFF'
                away_spread = 'OFF'

            if weights[2] > 0:
                total = round(values[2] / weights[2], 1)
            else:
                total = 'OFF'

            if weights[1] > 0 and weights[2] > 0:
                away_score = round((total - away_spread) / 2, 1)
                home_score = round((total - home_spread) / 2, 1)
            else:
                away_score = 'OFF'
                home_score = 'OFF'

            # requests.post('https://webhook.site/8c7e28a5-c43d-4ee5-b657-12afcdafddb8', data=dumps({"line" : 620}))
            # Prob and Edge Calculations
            home_spread_book = game['markets']['spread']['current']['home_spread']
            if home_spread_book[0] == '+':
                home_spread_book = float(home_spread_book[1:])
            else:
                home_spread_book = float(home_spread_book)

            home_spread_odds_book = game['markets']['spread']['current']['home']
            if home_spread_odds_book[0] == '+':
                home_spread_odds_book = float(home_spread_odds_book[1:])
            else:
                home_spread_odds_book = float(home_spread_odds_book)

            away_spread_book = game['markets']['spread']['current']['away_spread']
            if away_spread_book[0] == '+':
                away_spread_book = float(away_spread_book[1:])
            else:
                away_spread_book = float(away_spread_book)

            away_spread_odds_book = game['markets']['spread']['current']['away']
            if away_spread_odds_book[0] == '+':
                away_spread_odds_book = float(away_spread_odds_book[1:])
            else:
                away_spread_odds_book = float(away_spread_odds_book)

            home_ML_book = game['markets']['moneyline']['current']['home']
            if home_ML_book[0] == '+':
                home_ML_book = float(home_ML_book[1:])
            else:
                home_ML_book = float(home_ML_book)

            away_ML_book = game['markets']['moneyline']['current']['away']
            if away_ML_book[0] == '+':
                away_ML_book = float(away_ML_book[1:])
            else:
                away_ML_book = float(away_ML_book)

            total_book = float(game['markets']['total']['current']['total'])

            over_odds_book = game['markets']['total']['current']['over']
            if over_odds_book[0] == '+':
                over_odds_book = float(over_odds_book[1:])
            else:
                over_odds_book = float(over_odds_book)

            under_odds_book = game['markets']['total']['current']['under']
            if under_odds_book[0] == '+':
                under_odds_book = float(under_odds_book[1:])
            else:
                under_odds_book = float(under_odds_book)

                # requests.post('https://webhook.site/8c7e28a5-c43d-4ee5-b657-12afcdafddb8', data=dumps({"line" : 671}))

            home_prob_book = prob_from_am(home_ML_book)
            away_prob_book = prob_from_am(away_ML_book)
            home_prob_book = home_prob_book / (home_prob_book + away_prob_book)
            away_prob_book = away_prob_book / (home_prob_book + away_prob_book)

            book_z_score = norm.ppf(home_prob_book, 0, 1)
            book_stdev = (-home_spread_book) / book_z_score
            # print(home_spread_book, home_prob_book, book_z_score, book_stdev)

            home_prob = norm.cdf(0, home_spread, book_stdev)
            away_prob = 1.0 - home_prob

            # requests.post('https://webhook.site/8c7e28a5-c43d-4ee5-b657-12afcdafddb8', data=dumps({"line" : 684}))
            # Prediction
            if home_spread > 0:
                home_spread_str = f"+{home_spread}"
            elif home_spread < 0:
                home_spread_str = str(home_spread)
            else:
                home_spread_str = "PICK"

            if away_spread > 0:
                away_spread_str = f"+{away_spread}"
            elif away_spread < 0:
                away_spread_str = str(away_spread)
            else:
                away_spread_str = "PICK"

            home_ML = am_from_prob(home_prob)
            away_ML = am_from_prob(away_prob)

            pred = {
                'away_spread': away_spread_str,
                'home_spread': home_spread_str,
                'away_moneyline': away_ML,
                'home_moneyline': home_ML,
                'over_total': str(total),
                'under_total': str(total)
            }

            # requests.post('https://webhook.site/8c7e28a5-c43d-4ee5-b657-12afcdafddb8', data=dumps({"line" : 714}))
            # Probability
            home_spread_prob = norm.cdf(home_spread_book, home_spread, book_stdev)
            away_spread_prob = 1.0 - home_spread_prob
            over_prob = 1.0 - norm.cdf(total_book, total, book_stdev)
            under_prob = 1.0 - over_prob

            home_spread_prob_str = f"{round(100.0 * home_spread_prob, 1)}%"
            away_spread_prob_str = f"{round(100.0 * away_spread_prob, 1)}%"

            home_moneyline_prob_str = f"{round(100.0 * home_prob, 1)}%"
            away_moneyline_prob_str = f"{round(100.0 * away_prob, 1)}%"

            over_prob_str = f"{round(100.0 * over_prob, 1)}%"
            under_prob_str = f"{round(100.0 * under_prob, 1)}%"

            prob = {
                'away_spread': away_spread_prob_str,
                'home_spread': home_spread_prob_str,
                'away_moneyline': away_moneyline_prob_str,
                'home_moneyline': home_moneyline_prob_str,
                'over_total': over_prob_str,
                'under_total': under_prob_str
            }

            # requests.post('https://webhook.site/8c7e28a5-c43d-4ee5-b657-12afcdafddb8', data=dumps({"line" : 739}))
            # Edge
            home_spread_prob_book = prob_from_am(home_spread_odds_book)
            away_spread_prob_book = prob_from_am(away_spread_odds_book)
            home_spread_edge = home_spread_prob - home_spread_prob_book
            away_spread_edge = away_spread_prob - away_spread_prob_book
            home_spread_edge_str = f"{round(100.0 * home_spread_edge, 1)}%"
            away_spread_edge_str = f"{round(100.0 * away_spread_edge, 1)}%"

            # print(home_prob, away_prob, home_prob_book, away_prob_book)
            home_ML_edge = home_prob - home_prob_book
            away_ML_edge = away_prob - away_prob_book
            home_ML_edge_str = f"{round(100.0 * home_ML_edge, 1)}%"
            away_ML_edge_str = f"{round(100.0 * away_ML_edge, 1)}%"

            under_prob_book = prob_from_am(under_odds_book)
            over_prob_book = prob_from_am(over_odds_book)
            under_edge = under_prob - under_prob_book
            over_edge = over_prob - over_prob_book
            under_edge_str = f"{round(100.0 * under_edge, 1)}%"
            over_edge_str = f"{round(100.0 * over_edge, 1)}%"

            edge = {
                'away_spread': away_spread_edge_str,
                'home_spread': home_spread_edge_str,
                'away_moneyline': away_ML_edge_str,
                'home_moneyline': home_ML_edge_str,
                'over_total': over_edge_str,
                'under_total': under_edge_str
            }

            # requests.post('https://webhook.site/8c7e28a5-c43d-4ee5-b657-12afcdafddb8', data=dumps({"line" : 770}))
            # Expected Value
            home_spread_dec = float(game['markets']['spread']['current']['home_dec'])
            away_spread_dec = float(game['markets']['spread']['current']['away_dec'])
            home_ML_dec = float(game['markets']['moneyline']['current']['home_dec'])
            away_ML_dec = float(game['markets']['moneyline']['current']['away_dec'])
            over_dec = float(game['markets']['total']['current']['over_dec'])
            under_dec = float(game['markets']['total']['current']['under_dec'])

            home_spread_EV = home_spread_prob * home_spread_dec - 1.0
            away_spread_EV = away_spread_prob * away_spread_dec - 1.0
            home_ML_EV = home_prob * home_ML_dec - 1.0
            away_ML_EV = away_prob * away_ML_dec - 1.0
            under_EV = under_prob * under_dec - 1.0
            over_EV = over_prob * over_dec - 1.0

            home_spread_EV_str = f"{round(100.0 * home_spread_EV, 1)}%"
            away_spread_EV_str = f"{round(100.0 * away_spread_EV, 1)}%"
            home_ML_EV_str = f"{round(100.0 * home_ML_EV, 1)}%"
            away_ML_EV_str = f"{round(100.0 * away_ML_EV, 1)}%"
            over_EV_str = f"{round(100.0 * over_EV, 1)}%"
            under_EV_str = f"{round(100.0 * under_EV, 1)}%"

            EV = {
                'away_spread': away_spread_EV_str,
                'home_spread': home_spread_EV_str,
                'away_moneyline': away_ML_EV_str,
                'home_moneyline': home_ML_EV_str,
                'over_total': over_EV_str,
                'under_total': under_EV_str
            }

            # requests.post('https://webhook.site/8c7e28a5-c43d-4ee5-b657-12afcdafddb8', data=dumps({"line" : 802}))
            # Kelly Criterion
            away_spread_kelly = 0.0
            home_spread_kelly = 0.0
            away_ML_kelly = 0.0
            home_ML_kelly = 0.0
            over_kelly = 0.0
            under_kelly = 0.0

            book_res = book_table.get_item(Key={'username': user_id})
            book_list = book_res.get('Item', {}).get('book_list', [])
            for book_data in book_list:
                if book_data.get('id', 'none') == game.get('markets', {}).get('book', 'no_book'):
                    book_balance = float(book_data.get('bookBalance', 0.0))
                    if book_balance > 0.0:
                        away_spread_kelly = round(
                            max((book_balance * (away_spread_prob + (away_spread_prob - 1) / (away_spread_dec - 1))),
                                0.00), 2)
                        home_spread_kelly = round(
                            max((book_balance * (home_spread_prob + (home_spread_prob - 1) / (home_spread_dec - 1))),
                                0.00), 2)
                        away_ML_kelly = round(
                            max((book_balance * (away_prob + (away_prob - 1) / (away_ML_dec - 1))), 0.00), 2)
                        home_ML_kelly = round(
                            max((book_balance * (home_prob + (home_prob - 1) / (home_ML_dec - 1))), 0.00), 2)
                        over_kelly = round(max((book_balance * (over_prob + (over_prob - 1) / (over_dec - 1))), 0.00),
                                           2)
                        under_kelly = round(
                            max((book_balance * (under_prob + (under_prob - 1) / (under_dec - 1))), 0.00), 2)

            kelly = {
                'away_spread': f"${away_spread_kelly}",
                'home_spread': f"${home_spread_kelly}",
                'away_moneyline': f"${away_ML_kelly}",
                'home_moneyline': f"${home_ML_kelly}",
                'over_total': f"${over_kelly}",
                'under_total': f"${under_kelly}"
            }

            engine_response = {
                'away_score': away_score,
                'home_score': home_score,
                'away_spread': away_spread,
                'home_spread': home_spread,
                'away_prob': round(away_prob, 4),
                'home_prob': round(home_prob, 4),
                'total': total,
                'prediction': pred,
                'probability': prob,
                'edge': edge,
                'EV': EV,
                'kelly': kelly
            }
            # requests.post('https://webhook.site/8c7e28a5-c43d-4ee5-b657-12afcdafddb8', data=dumps({"line" : 849}))
        return engine_response

    except Exception as error:
        return f"{error}"


def game_log(sr_id):
    log_table = db.Table('nfl-game-log')
    res = log_table.get_item(Key={'sr_id': sr_id})
    data = res.get('Item')
    if data:
        summary = data.get('summary')

        if 'summary' in data: del data['summary']
        if 'statistics' in data: del data['statistics']

        home_score = str(summary.get('home').get('points', 0))
        away_score = str(summary.get('away').get('points', 0))

        data.update({
            'home_score': home_score,
            'away_score': away_score
        })

        if data.get('status') == 'closed':
            if data['quarter'] == 5:
                data['quarter'] = 'FINAL/OT'
            else:
                data['quarter'] = 'FINAL'
            data['clock'] = f"{away_score}-{home_score}"

    return data


def get_record(sr_id):
    res = stats_table.get_item(Key={'sr_id': sr_id, 'year': '2021'})
    data = res.get('Item')
    team_record = data.get('season_record', '0-0-0')

    return team_record


def lambda_handler(event):
    user = event.get("user")

    week = event.get("week", False)
    book_id = event.get("book")

    ct = 0
    if week:
        games = getAllData(week)
        games_list = []
        for game in games:
            # The following code can be used to add data from other tables as needed
            game_id = game.get('id')  # Modified logic for error-handling if sr_id is missing
            if game_id:
                # Add Odds Data
                sr_id = get_sr_id(game_id)
                # print(sr_id)
                game.update({'sr:match:id': sr_id})
                market_data = getOdds(sr_id, book_id)
                game.update({'markets': market_data})

                # Add Bet Percentage Data
                bet_percentage = get_bet_percentage(sr_id)
                game.update({'bet_percentage': bet_percentage})

                # Add Team Logo URL
                # game['venue']['sr_match_id'] = sr_id
                away_team_id = game.get('away').get('sr_id')
                home_team_id = game.get('home').get('sr_id')
                game['home']['logo'] = LOGO_URL + home_team_id + '.png'
                game['away']['logo'] = LOGO_URL + away_team_id + '.png'

                # Add Team Record (Placeholder)
                # game['home'].update({'record': '0-0-0'})
                # game['away'].update({'record': '0-0-0'})
                game['home'].update({'record': get_record(home_team_id)})
                game['away'].update({'record': get_record(away_team_id)})

                # Add Broadcast Info String
                if game.get('scheduled'):
                    game_datetime = datetime.strptime(game['scheduled'], '%Y-%m-%dT%H:%M:%S%z')
                    game_datetime.replace(tzinfo=timezone('UTC'))
                    game_est = game_datetime.astimezone(timezone('US/Eastern'))
                    game_time = datetime.strftime(game_est, '%a %m-%d-%y %I:%M%p')
                    game_desc = datetime.strftime(game_est, '%m/%d/%y %I:%M%p')
                    if game.get('broadcast', False):
                        network = game['broadcast'].get('network', 'TBD')
                    else:
                        network = 'TBD'
                info_string = game_time + " on " + network
                game['broadcast'].update({'info': info_string})
                game['broadcast'].update({'desc': game_desc})

                # Add Week Info String
                week_info = 'Week ' + str(week)
                game.update({'week': week_info})

                # Get Game Projections
                projection_data = get_projections(game, week)
                game.update({'projections': projection_data})

                # Get Engine Results
                engine_results = engine_calcs(user.email, game)
                # # engine_results = game
                game.update({'engine_results': engine_results})

                # Get Live Game Log
                game_log_data = game_log(sr_id)
                game.update({'game_log': game_log_data})

            games_list.append(game)

        games_list.sort(key=lambda x: x['broadcast']['desc'])

        res = already_bet_placed_data(games_list, book_id, user.email)

        ############################################
        #           Matchup view logic
        ###########################################

        result = matchup_view(user.email, book_id, res)

        return {
            'statusCode': 200,
            'body': result,
        }

    else:
        return {
            'statusCode': 200,
            'body': getAllWeek(),
        }
