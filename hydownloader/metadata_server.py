#!/usr/bin/env python3

# hydownloader
# Copyright (C) 2021  thatfuckingbird

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import click

@click.group()
def cli() -> None:
    pass

@cli.command(help='Start metadata server.')
@click.option('--path', type=str, required=True, help='hydownloader database path.')
def start(path: str) -> None:
    raise NotImplementedError()

def main() -> None:
    cli()
    ctx = click.get_current_context()
    click.echo(ctx.get_help())
    ctx.exit()

if __name__ == "__main__":
    main()
