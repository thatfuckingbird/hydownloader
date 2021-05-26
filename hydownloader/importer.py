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
import hydrus
from hydownloader import db
import json
from typing import Optional

@click.group()
def cli() -> None:
    pass

@cli.command(help='Run an import job to transfer files and metadata into Hydrus.')
@click.option('--path', type=str, required=True, help='hydownloader database path.')
@click.option('--job', type=str, required=True, help='Hydrus database directory (where the .db files are located).')
@click.option('--config', type=str, required=False, default=None, help='Import job configuration filepath override.')
def run_job(path: str, job: str, config: Optional[str]) -> None:
    log.init(path, True)
    db.init(path)

    config_path = db.get_rootpath()+'/hydownloader-import-jobs.json'
    if config:
        config_path = config
    if not os.path.isfile(config_path):
        log.fatal("hydownloader-importer", f"Configuration file not found: {config_path}")

    jobs = json.load(open(config_path, 'r', encoding='utf-8-sig'))
    if not job in jobs:
        log.fatal("hydownloader-importer", f"Job not found in configuration file: {job}")
    jd = jobs[job]

    client = hydrus.Client(jd['apiKey'], jd['apiURL'])

def main() -> None:
    cli()
    ctx = click.get_current_context()
    click.echo(ctx.get_help())
    ctx.exit()

if __name__ == "__main__":
    main()
