import json
import boto3
import copy

# Set up AWS Resources
db = boto3.resource('dynamodb')
stats_table = db.Table('nfl_season_stats')
data_table = db.Table('nfl_team_profile')
roster_table = db.Table('nfl_team_roster')
proj_table = db.Table('nfl_rotowire_projections')

current_week = "1"


def get_stats(team_id):
    response = stats_table.get_item(Key={'sr_id': team_id})
    return response.get('Item')


def get_team_data(team_id):
    response = data_table.get_item(Key={'sr_id': team_id})
    return response.get('Item')


def get_team_roster(team_id):
    response = roster_table.get_item(Key={'sr_id': team_id})
    return response.get('Item')


def get_team_stats(stats, side, period):
    # Choose Offense or Defense
    if side == 'off':
        team_stats = stats.get('record', {})
    elif side == 'def':
        team_stats = stats.get('opponents', {})

    # Choose Full Season or Per Game
    games = team_stats.get('games_played', 0)
    factor = 1
    if period == 'per_game' and games > 0: factor = copy.deepcopy(games)

    # Scoring
    td = team_stats.get('touchdowns', {}).get('total', 0)
    fg = team_stats.get('field_goals', {}).get('made', 0)
    xp = team_stats.get('extra_points', {}).get('kicks', {}).get('made', 0)
    tpc = team_stats.get('extra_points', {}).get('conversions', {}).get('pass_successes', 0) + team_stats.get(
        'extra_points', {}).get('conversions', {}).get('rush_successes', 0)
    pts = 6 * td + 3 * fg + xp + 2 * tpc

    # Yards
    rush_stats = team_stats.get('rushing', {})
    pass_stats = team_stats.get('passing', {})
    rush_yards = rush_stats.get('yards', 0)
    pass_yards = pass_stats.get('gross_yards', 0)
    net_pass_yards = pass_stats.get('net_yards', 0)
    total_yards = rush_yards + pass_yards
    rush_attempts = rush_stats.get('attempts', 0)
    pass_attempts = pass_stats.get('attempts', 0)

    # Rates
    rush_ypa = round(rush_yards / rush_attempts, 1)
    pass_ypa = round(pass_yards / pass_attempts, 1)
    net_ypa = round(net_pass_yards / pass_attempts, 1)
    ypp = round(total_yards / pts, 1)

    # Turnovers
    interceptions = pass_stats.get('interceptions', 0)
    fumbles = team_stats.get('fumbles', {}).get('lost_fumbles', 0)
    turnovers = interceptions + fumbles

    # Efficiency
    efficiency = team_stats.get('efficiency', {})
    third_down = efficiency.get('thirddown', {}).get('pct')

    # Penalties
    penalty = team_stats.get('penalties', {})
    penalties = penalty.get('penalties', 0)
    pen_yards = penalty.get('yards', 0)

    return {
        'games': games,
        'points': round(pts / factor, 1),
        'touchdowns': round(td / factor, 1),
        'field_goals': round(fg / factor, 1),
        'extra_points': round(xp / factor, 1),
        '2pt_conversions': round(tpc / factor, 1),
        'rush_yards': round(rush_yards / factor, 1),
        'pass_yards': round(pass_yards / factor, 1),
        'net_yards': round(net_pass_yards / factor, 1),
        'total_yards': round(total_yards / factor, 1),
        'rush_attempts': round(rush_attempts / factor, 1),
        'pass_attempts': round(pass_attempts / factor, 1),
        'rush_ypa': rush_ypa,
        'pass_ypa': pass_ypa,
        'net_ypa': net_ypa,
        'yards_pt': ypp,
        'turnovers': round(turnovers / factor, 1),
        'third_down_eff': round(third_down, 1),
        'penalties': round(penalties / factor, 1),
        'pen_yards': round(pen_yards / factor, 1)
    }


def get_player_stats(data, period):
    players = data.get('players', [])

    pass_list = []
    rush_list = []
    rec_list = []
    def_list = []
    spc_list = []

    for player in players:
        games = player.get('games_played', 0)
        factor = 1
        if period == 'per_game' and games > 0: factor = copy.deepcopy(games)

        name = player.get('name')
        name_list = name.split()
        first_name = name_list[0]
        first_init = first_name[:1]
        last_name = name_list[1]
        abv_name = first_init + "." + last_name

        player_info = {
            'sr_id': player.get('sr_id'),
            'uuid': player.get('id'),
            'name': player.get('name'),
            'abv_name': abv_name,
            'position': player.get('position'),
            'number': player.get('jersey'),
            'games_played': games
        }

        # Passing Stats
        if player.get('passing', False):
            pass_data = player['passing']
            if pass_data.get('attempts', 0) > 0:
                pass_stats = {
                    'attempts': round(pass_data.get('attempts', 0) / factor, 1),
                    'completions': round(pass_data.get('completions', 0) / factor, 1),
                    'comp_pct': round(pass_data.get('cmp_pct', 0), 1),
                    'pass_yards': round(pass_data.get('yards', 0) / factor, 1),
                    'pass_ypa': round(pass_data.get('yards', 0) / pass_data.get('attempts', 0), 1),
                    'pass_td': round(pass_data.get('touchdowns', 0) / factor, 1),
                    'interceptions': round(pass_data.get('interceptions', 0) / factor, 1),
                    'sacks': round(pass_data.get('sacks', 0) / factor, 1),
                    'rating': round(pass_data.get('rating', 0), 1)
                }
                pass_stats.update(player_info)
                pass_list.append(pass_stats)

        # Rushing Stats
        if player.get('rushing', False):
            rush_data = player['rushing']
            if rush_data.get('attempts', 0) > 0:
                rush_stats = {
                    'attempts': round(rush_data.get('attempts', 0) / factor, 1),
                    'rush_yards': round(rush_data.get('yards', 0) / factor, 1),
                    'rush_ypa': round(rush_data.get('yards', 0) / rush_data.get('attempts', 0), 1),
                    'rush_td': round(rush_data.get('touchdowns', 0) / factor, 1),
                    'fumbles': round(player.get('fumbles', {}).get('lost_fumbles', 0) / factor, 1)
                }
                rush_stats.update(player_info)
                rush_list.append(rush_stats)

        # Receiving Stats
        if player.get('receiving', False):
            rec_data = player['receiving']
            if rec_data.get('receptions', 0) > 0:
                rec_stats = {
                    'targets': round(rec_data.get('targets', 0) / factor, 1),
                    'receptions': round(rec_data.get('receptions', 0) / factor, 1),
                    'rec_yards': round(rec_data.get('yards', 0) / factor, 1),
                    'rec_ypc': round(rec_data.get('yards', 0) / rec_data.get('receptions', 0), 1),
                    'rec_td': round(rec_data.get('touchdowns', 0) / factor, 1),
                    'fumbles': round(player.get('fumbles', {}).get('lost_fumbles', 0) / factor, 1),
                    'YAC': round(rec_data.get('yards_after_catch', 0) / factor, 1)
                }
                rec_stats.update(player_info)
                rec_list.append(rec_stats)

        # Defensive Stats
        if player.get('defense', False):
            def_data = player['defense']
            tackles = def_data.get('tackles', 0)
            sacks = def_data.get('sacks', 0)
            interceptions = def_data.get('interceptions', 0)
            fumb_forced = def_data.get('forced_fumbles', 0)
            fumb_recovered = def_data.get('fumble_recoveries', 0)
            total_def_stats = tackles + sacks + interceptions + fumb_forced + fumb_recovered
            if total_def_stats > 0:
                def_stats = {
                    'tackles': round(tackles / factor, 1),
                    'sacks': round(sacks / factor, 1),
                    'interceptions': round(interceptions / factor, 1),
                    'fumbles_forced': round(fumb_forced / factor, 1),
                    'fumbles_recovered': round(fumb_recovered / factor, 1)
                }
                def_stats.update(player_info)
                def_list.append(def_stats)

        # Special Teams Stats
        if player.get('field_goals', False) or player.get('extra_points', False):
            fg_data = player.get('field_goals', {})
            xp_data = player.get('extra_points', {})
            if fg_data.get('attempts', 0) > 0 and fg_data.get('made', 0) > 0:
                FGA = fg_data.get('attempts', 0)
                FGM = fg_data.get('made', 0)
                FG_pct = round(100 * FGM / FGA, 1)
                tot_yds = fg_data.get('yards', 0)

                avg_yds = round(tot_yds / FGM, 0)

                XPA = xp_data.get('attempts', 0)
                XPM = xp_data.get('made', 0)
                if XPA > 0:
                    XP_pct = round(100 * XPM / XPA, 1)
                else:
                    XP_pct = 0.0
                spc_stats = {
                    'FGA': round(FGA / factor, 1),
                    'FGM': round(FGM / factor, 1),
                    'FG_pct': FG_pct,
                    'avg_yds': avg_yds,
                    'XPA': round(XPA / factor, 1),
                    'XPM': round(XPM / factor, 1),
                    'XP_pct': XP_pct
                }
                spc_stats.update(player_info)
                spc_list.append(spc_stats)

    return {
        'passing': pass_list,
        'rushing': rush_list,
        'receiving': rec_list,
        'defense': def_list,
        'spec_teams': spc_list
    }


def get_injuries(team):
    injury_table = db.Table('nfl_rotowire_injuries')
    response = injury_table.get_item(Key={'sr_id': team})
    injury_list = []
    for item in response.get('Item', {}).get('injuries', []):
        first_name = item.get('FirstName', "")
        last_name = item.get('LastName', "")
        name = first_name + " " + last_name
        first_init = first_name[:1]
        abv_name = first_init + "." + last_name
        position = item.get('Position')
        status = item.get('Injury', {}).get('Status', "")
        news = item.get('news', {}).get('Notes', 'No recent injury news.')
        raw_date = item.get('news', {}).get('DateTime', "")
        if raw_date == "":
            updated = "N/A"
        else:
            updated = raw_date[:10]

        injury_list.append({
            'name': name,
            'abv_name': abv_name,
            'position': position,
            'status': status,
            'news': news,
            'date': updated
        })

    return injury_list


def get_projections(team, week):
    # Initialize Stat Lists
    pass_list = []
    rush_list = []
    rec_list = []
    def_list = []
    spc_list = []

    roster_data = get_team_roster(team)
    for player in roster_data.get('players', []):

        # Populate Player Data
        player_id = player.get('id', False)

        if player_id:
            player_srid = player.get('sr_id')
            name = player.get('name')
            name_list = name.split()
            first_name = name_list[0]
            first_init = first_name[:1]
            last_name = name_list[1]
            abv_name = first_init + "." + last_name
            position = player.get('position')
            jersey = player.get('jersey')

            player_info = {
                'sr_id': player_srid,
                'uuid': player_id,
                'name': name,
                'abv_name': abv_name,
                'position': position,
                'number': jersey
            }

            # Get Rotowire Projection Data
            item = {
                'SportsDataId': player_id,
                'Week': week
            }
            response = proj_table.get_item(Key=item)
            data = response.get('Item', {})
            projections = data.get('Projections', {})

            # Passing Stats
            pass_attempts = projections.get('PassAttempts', 0)
            if pass_attempts > 0:
                completions = projections.get('PassCompletions', 0)
                comp_pct = 100.0 * round(float(completions / pass_attempts), 3)
                pass_yds = projections.get('PassYards', 0)
                pass_ypa = round(pass_yds / pass_attempts, 1)
                pass_td = projections.get('PassTouchdowns', 0)
                interceptions = projections.get('Interceptions', 0)
                sacks = projections.get('TimesSacked', 0)

                # Passer Rating Cacluation
                calc_a = (float(completions / pass_attempts) - 0.3) * 5.0
                fact_a = max(min(calc_a, 2.375), 0.0)

                calc_b = (float(pass_yds / pass_attempts) - 3.0) * 0.25
                fact_b = max(min(calc_b, 2.375), 0.0)

                calc_c = (float(interceptions / pass_attempts)) * 20.0
                fact_c = max(min(calc_c, 2.375), 0.0)

                calc_d = 2.375 - (float(pass_yds / pass_attempts)) * 25.0
                fact_d = max(min(calc_d, 2.375), 0.0)

                passer_rating = ((fact_a + fact_b + fact_c + fact_d) / 6.0) * 100.0

                pass_stats = {
                    'attempts': round(pass_attempts, 1),
                    'completions': round(completions, 1),
                    'comp_pct': round(comp_pct, 1),
                    'pass_yards': round(pass_yds, 1),
                    'pass_ypa': round(pass_ypa, 1),
                    'pass_td': round(pass_td, 1),
                    'interceptions': round(interceptions, 1),
                    'sacks': round(sacks, 1),
                    'rating': round(passer_rating, 2)
                }

                pass_stats.update(player_info)
                pass_list.append(pass_stats)

            # Rushing Stats
            rush_attempts = projections.get('RushAttempts', 0)
            if rush_attempts > 0:
                rush_yds = projections.get('RushYards', 0)
                rush_ypa = round(rush_yds / rush_attempts, 1)
                rush_td = projections.get('RushTouchdowns', 0)
                fumbles = projections.get('FumblesLost', 0)

                rush_stats = {
                    'attempts': round(rush_attempts, 1),
                    'rush_yards': round(rush_yds, 1),
                    'rush_ypa': round(rush_ypa, 1),
                    'rush_td': round(rush_td, 1),
                    'fumbles': round(fumbles, 1)
                }

                rush_stats.update(player_info)
                rush_list.append(rush_stats)

            # Receiving Stats
            targets = projections.get('Targets', 0)
            if targets > 0:
                receptions = projections.get('Receptions', 0)
                rec_yds = projections.get('ReceivingYards', 0)
                rec_ypc = round(rec_yds / receptions, 1)
                rec_td = projections.get('ReceivingTouchdowns', 0)
                fumbles = projections.get('FumblesLost', 0)

                rec_stats = {
                    'targets': round(targets, 1),
                    'receptions': round(receptions, 1),
                    'rec_yards': round(rec_yds, 1),
                    'rec_ypc': round(rec_ypc, 1),
                    'rec_td': round(rec_td, 1),
                    'fumbles': round(fumbles, 1)
                }

                rec_stats.update(player_info)
                rec_list.append(rec_stats)

                # Defensive Stats
            def_positions = {
                'DT': 'Defensive Tackle',
                'DE': 'Defensive End',
                'LB': 'Linebacker',
                'CB': 'Cornerback',
                'DB': 'Defensive Back',
                'S': 'Safety'
            }
            if position in def_positions:
                tackles = projections.get('TotalTackles', 0)
                sacks = projections.get('Sacks', 0)
                interceptions = projections.get('Interceptions', 0)
                fumb_forced = projections.get('FumblesForced', 0)
                fumb_recovered = projections.get('FumblesRecovered', 0)
                total_def_stats = tackles + sacks + interceptions + fumb_forced + fumb_recovered
            else:
                total_def_stats = 0

            if total_def_stats > 0:
                def_stats = {
                    'tackles': round(tackles, 1),
                    'sacks': round(sacks, 1),
                    'interceptions': round(interceptions, 1),
                    'fumbles_forced': round(fumb_forced, 1),
                    'fubmles_recovered': round(fumb_recovered, 1)
                }

                def_stats.update(player_info)
                def_list.append(def_stats)

                # Special Teams Stats
            FGA = projections.get('FieldGoalAttempts', 0)
            if FGA > 0:
                FGM = projections.get('FieldGoalsMade', 0)
                FG_pct = 100.0 * float(FGM / FGA)
                XPA = projections.get('ExtraPointAttempts', 0)
                XPM = projections.get('ExtraPointsMade', 0)
                if XPA > 0:
                    XP_pct = 100.0 * float(XPM / XPA)
                else:
                    XP_pct = 0.0

                    # Average Yards Calculation
                FGM_u20 = float(projections.get('FieldGoalsMadeUnder20', 0.0))
                FGM_20_29 = float(projections.get('FieldGoalsMade20To29', 0.0))
                FGM_30_39 = float(projections.get('FieldGoalsMade30To39', 0.0))
                FGM_40_49 = float(projections.get('FieldGoalsMade40To49', 0.0))
                FGM_o50 = float(projections.get('FieldGoalsMade50Plus', 0.0))
                avg_yds = (
                                  20.0 * FGM_u20 + 25.0 * FGM_20_29 + 35.0 * FGM_30_39 + 45.0 * FGM_40_49 + 50.0 * FGM_o50) / float(
                    FGM)

                spc_stats = {
                    'FGA': round(FGA, 1),
                    'FGM': round(FGM, 1),
                    'FG_pct': round(FG_pct, 1),
                    'avg_yds': round(avg_yds, 1),
                    'XPA': round(XPA, 1),
                    'XPM': round(XPM, 1),
                    'XP_pct': round(XP_pct, 1)
                }

                spc_stats.update(player_info)
                spc_list.append(spc_stats)

    return {
        'passing': pass_list,
        'rushing': rush_list,
        'receiving': rec_list,
        'defense': def_list,
        'spec_teams': spc_list
    }


def lambda_handler(event):

    
    team = event.get('team')
    data = get_stats(team)
    if 'week' in event:
        week = event.get('week')
    else:
        week = current_week

    team_data = {
        'profile': get_team_data(team),
        'offense': {
            "season_total": get_team_stats(data, 'off', 'season'),
            "per_game": get_team_stats(data, 'off', 'per_game')
        },
        'defense': {
            "season_total": get_team_stats(data, 'def', 'season'),
            "per_game": get_team_stats(data, 'def', 'per_game')
        },
        'players': {
            "season_total": get_player_stats(data, 'season'),
            "per_game": get_player_stats(data, 'per_game'),
            'projections': get_projections(team, week)
        },
        'injuries': get_injuries(team)
    }

    # Need to add: Injuries, News, Projections - Rotowire/CDFS, Ratings?

    return {
        'statusCode': 200,
        'body': team_data
    }
