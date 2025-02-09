from fasthtml.common import *
from dataclasses import dataclass


def render(pick):
    pid = f'pick-{pick.id}'
    return Tr(
        Td(pid),
        Td(pick.id),
        Td(pick.pickname), Td(pick.tier1_pick), Td(pick.tier2_pick), Td(pick.tier3_pick), Td(pick.tier4_pick), 
        Td(
            Button(
                'delete', 
                hx_delete=f'/pick/{pick.id}', 
                hx_swap='outerHTML', 
                target_id=pid, 
                style='background-color:red; border-color:red;'
            )
        ),
        id=pid
    )

app,rt,picks,Pick = fast_app(
    'picks.db', live=True, render=render,
    id=int, pickname=str, tier1_pick=str, tier2_pick=str, tier3_pick=str, tier4_pick=str, pk='id')

"""
tables:
* golfers
    * name
    * odds?
    * tournament
    * tier
    * 1st round score 
    * 2nd round score 
    * 3rd round score 
    * 4th round score 
* players
    * name
    * groupme username
* picks
    * player name
    * pick name (need this if a player has more than 1 pick - maybe auto-generate?)
    * tier 1 pick
    * tier 2 pick
    * tier 3 pick
    * tier 4 pick
* tournaments
    * name
    * date
    * location
"""

@dataclass
class Pick:
    pickname: str
    tier1_pick: str
    tier2_pick: str
    tier3_pick: str
    tier4_pick: str

def validate_pick(pick: Pick):
    errors = []
    print(pick)
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

    return errors

def options(tier):
    return (
        Option(f'Select a player from tier {tier}'),
        Option(f'tier{tier}: option 1'),
        Option(f'tier{tier}: option 2'),
        Option(f'tier{tier}: option 3')
    )

def select_player(tier : int):
    return Select(options(tier), placeholder=f'Select tier {tier} player', name=f'tier{tier}_pick')

@app.get('/')
def home(): 
    return Title("Golf Pick'em"), Main(
        H1("Golf Pick'em"),
        Form(
            Input(placeholder=f"Set pick name", name='pickname'),
            Grid(
                select_player(1),
                select_player(2),
                select_player(3),
                select_player(4)
            ),
            Button('Submit'),
            hx_post="/submit",
            hx_target="#picks-list",
            hx_swap="beforeend",
            hx_swap_oob='true'
        ),
        Div(id="notes"),
        Table(
            Tr(Th('Pick Name'), Th('Tier 1'), Th('Tier 2'), Th('Tier 3'), Th('Tier 4'), Th('')),
            *picks(), id='picks-list')
    )

@app.post('/submit')
def submit(pick: Pick):
    errors = validate_pick(pick)
    if errors:
        return Div(Ul(*[Li(error, style="color: red;") for error in errors]), id="notes")
    
    return picks.insert(pick) # , Div('Submitted successfully', id='notes', style="color: green;")

@app.delete('/pick/{pid}')
def delete_pick(pid:int): 
    print(pid)
    picks.delete(pid)

serve()