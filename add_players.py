import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.db import get_session
from warehouse.crud import WarehouseCRUD

VALID_POSITIONS = {"GK", "DEF", "MID", "FWD"}


def main() -> None:
    with get_session() as session:
        crud = WarehouseCRUD(session)

        team_name = input("Team name: ").strip()
        team = crud.get_or_create_team(team_name)
        print(f"Using team: {team.name} (id={team.id})\n")

        print("Enter players one at a time. Blank name to finish.\n")
        added = 0
        while True:
            name = input("Player name: ").strip()
            if not name:
                break

            position = input("Position (GK/DEF/MID/FWD): ").strip().upper()
            if position not in VALID_POSITIONS:
                print(f"  Invalid position '{position}', skipping this player.")
                continue

            player = crud.get_or_create_player(name, team.id, position)
            print(f"  Added: {player.name} ({player.position}) [id={player.id}]\n")
            added += 1

        print(f"\nDone. {added} player(s) added/confirmed for {team.name}.")


if __name__ == "__main__":
    main()