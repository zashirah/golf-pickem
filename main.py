from fasthtml.common import *
from dataclasses import dataclass

db = database('data/golf_pickem.db')

tournaments,picks,golfers,tournament_golfers = db.t.tournaments,db.t.picks,db.t.golfers,db.t.tournament_golfers

if tournaments not in db.t:
    tournaments.create(id=int, name=str, current=bool, allow_submissions=bool, pk='id')
Tournament = tournaments.dataclass()

if picks not in db.t:
    picks.create(id=int, pickname=str, tier1_pick=str, tier2_pick=str, tier3_pick=str, tier4_pick=str, tournament_id=int, pk='id')
Pick = picks.dataclass()

if golfers not in db.t:
    golfers.create(id=int, name=str, pk='id')
Golfer = golfers.dataclass()

if tournament_golfers not in db.t:
    tournament_golfers.create(id=int, tournament_id=int, golfer_id=int, pk='id')
TournamentGolfers = tournament_golfers.dataclass()

@patch
def __ft__(self:Pick):
    pid = f'pick-{self.id}'
    return Tr(Td(self.tournament_id),
        Td(self.pickname), Td(self.tier1_pick), Td(self.tier2_pick), Td(self.tier3_pick), Td(self.tier4_pick), 
        Td(
            Button(
                'delete', 
                hx_delete=f'/picks/{self.id}', 
                hx_swap='outerHTML', 
                target_id=pid, 
                style='background-color:red; border-color:red;'
            )
        ),
        id=pid
    )

@patch
def __ft__(self:Tournament):
    tid = f'tournament-{self.id}'
    return Tr(
        Td(self.name), Td(self.current), Td(self.allow_submissions),
        Td(
            Button(
                'Delete', 
                hx_delete=f'/tournaments/{self.id}', 
                hx_swap='outerHTML', 
                target_id=tid, 
                style='background-color:red; border-color:red;'
            )
        ), 
        Td(Button(
                'Set Not Current' if self.current else 'Set Current', 
                hx_patch=f'/tournaments/{self.id}/current', 
                hx_swap='outerHTML', 
                target_id=tid, 
                style='background-color:green; border-color:green;',
            )
        ),
        Td(Button(
                'Disallow Submissions ' if self.allow_submissions else 'Allow Submissions', 
                hx_patch=f'/tournaments/{self.id}/submissions', 
                hx_swap='outerHTML', 
                target_id=tid, 
                style='background-color:green; border-color:green;',
            )
        ),
        Td(Button(
                'Download Field', 
                hx_get=f'/tournaments/{self.id}/field', 
                style='background-color:green; border-color:green;',
            )
        ),
        id=tid
    )

app,rt = fast_app(live=True)

"""
tables:
    * golfers
        * name
        * odds?
        * tournament
    * tournaments
        * name
        * date
        * location
    * tournament_golfer
        * tournament
        * tier
        * round
        * score
        * hole
    * users
        * name
        * groupme username
    * picks
        * player name
        * pick name (need this if a player has more than 1 pick - maybe auto-generate?)
        * tier 1 pick
        * tier 2 pick
        * tier 3 pick
        * tier 4 pick
"""

def options(tier:int):
    return (
        Option(f'Select a player from tier {tier}'),
        Option(f'option 1'),
        Option(f'option 2'),
        Option(f'option 3'),
        Option(f'option 4')
    )

def tournament_options():
    return Div(*[Option(t.name) for t in tournaments(order_by="current")])

def select_player(tier:int): return Select(options(tier), placeholder=f'Select tier {tier} player', name=f'tier{tier}_pick')

def update_form(page=None):
    if page == 'picks':
        return Div(Form(
            H3('Make your pick'),
            Div(
                Input(placeholder=f"Pick Name", name='pickname'),
            ),
            Grid(
                select_player(1),
                select_player(2),
                select_player(3),
                select_player(4)
            ),
            Button('Submit'),
            hx_post="/picks",
            hx_target="#picks-list",
            hx_swap="beforeend",
            hx_swap_oob='true'
        ), hx_swap_oob='true', id='form')
    elif page == 'tournaments':
        return Div(Form(
            H3('Create Tournament'),
            Grid(
                Input(placeholder="Tournment Name", name="name"),
                Div(
                    Label("Current", Input(type="Checkbox", name="current")),
                    Label("Allow Submissions", Input(type="Checkbox", name="allow_submissions")),
                ),
            ),
            Button('Submit'),
            hx_post="/tournaments",
            hx_target="#tournaments-list",
            hx_swap="beforeend",
            hx_swap_oob='true'
        ), hx_swap_oob='true', id='form')
    elif not page:
        return Div(id='form')

def get_header():
    return Header(
            Grid(
                H1("Golf Pick'em"),
                Button("Pick'em", hx_get='/picks', hx_swap_oob='true', hx_target="#home"),
                Button('Tournaments', hx_get='/tournaments', hx_swap_oob='true', hx_target="#home"),
            )
        )

@app.get('/')
def home(): 
    return Main(
        get_header(),
        H2(tournaments(where="allow_submissions=1")[0].name),
        update_form(),
        Main(id='home')
    )

### TOURNAMENTS
@app.get('/tournaments')
def get_tournaments(): 
    return Div(
        Table(
            Tr(Th('Tournament Name'), Th('Current'), Th('Allow Submissions'), Th(' '), Th(' ')),
            *tournaments(), id='tournaments-list'
        ),
        id='home'
    ), update_form(page='tournaments')

def validate_tournament(tournament: Tournament): return True if tournament.name else False

@app.post('/tournaments')
def post_tournaments(tournament: Tournament): 
    if validate_tournament(tournament):
        return tournaments.insert(tournament)
    
@app.delete('/tournaments/{tid}')
def delete_tournament(tid:int): tournaments.delete(tid)

@app.patch('/tournaments/{tid}/current')
def patch_tournament_current(tid:int): 
    t = tournaments[tid]
    t.current = not t.current
    return tournaments.update(t)

@app.patch('/tournaments/{tid}/submissions')
def patch_tournament_submissions(tid:int): 
    t = tournaments[tid]
    t.allow_submissions = not t.allow_submissions
    return tournaments.update(t)

### PICKS 
@app.get('/picks')
def get_picks():
    return Div(
        Table(
            Tr(Th('Pick Name'), Th('Tier 1'), Th('Tier 2'), Th('Tier 3'), Th('Tier 4'), Th(' ')),
            *picks(), id='picks-list'
        ),
        id='home'
    ), update_form('picks')

def validate_pick(pick: Pick):
    errors = []
    if len(pick.pickname) < 1:
        errors.append('Must include username')
    if pick.tier1_pick == f'Select a player from tier 1':
        errors.append('Must include a pick from tier 1')
    if pick.tier2_pick == f'Select a player from tier 2':
        errors.append('Must include a pick from tier 2')
    if pick.tier3_pick == f'Select a player from tier 3':
        errors.append('Must include a pick from tier 3')
    if pick.tier4_pick == f'Select a player from tier 4':
        errors.append('Must include a pick from tier 4')

    return False if errors else True

@app.post('/picks')
def post_picks(pick: Pick): 
    print(pick)
    if validate_pick(pick):
        pick.tournament_id = tournaments(where="allow_submissions=1")[0].id
        return picks.insert(pick)

@app.delete('/picks/{pid}')
def delete_pick(pid:int): picks.delete(pid)

serve()
