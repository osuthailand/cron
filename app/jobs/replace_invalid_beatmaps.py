import asyncio
from datetime import datetime, timedelta
import os
import aiohttp
from dataclasses import dataclass
from pathlib import Path
from databases import Database
from redis import Redis
from app.objects.framework import Job, config

BEATMAPS_DIRECTORY = Path(os.environ["BEATMAPS_DIRECTORY"])
HTTP_459_RESPONSE = """
<html>                                                                                                                                     
<head><title>429 Too Many Requests</title></head>                                                                                          
<body>                                                                                                                                     
<center><h1>429 Too Many Requests</h1></center>                                                                                            
<hr><center>nginx</center>                                                                                                                 
</body>                                                                                                                                    
</html> 
"""


@dataclass
class DotOsuEndpoint:
    host: str
    endpoint: str
    ratelimit_pause: datetime | None = None
    corrected_files: int = 0


BANCHO_OSU_ENDPOINT = DotOsuEndpoint(
    host="bancho",
    endpoint="https://osu.ppy.sh/web/osu-getosufile.php?q={map_id}",
)
MINO_OSU_ENDPOINT = DotOsuEndpoint(
    host="mino",
    endpoint="https://catboy.best/osu/{map_id}?raw=1",
)


@config.register(name="replace_invalid_beatmaps", interval=86400)  # every day
async def replace_invalid_beatmaps(job: Job, database: Database, redis: Redis) -> None:
    """
    `replace_invalid_beatmaps()` replaces all .osu files in the server directory that
    has been wrongfully saved.
    """

    client_session = aiohttp.ClientSession()
    mirror_order = (BANCHO_OSU_ENDPOINT, MINO_OSU_ENDPOINT)
    corrupted = 0

    print("Started looking through all saved .osu files.")

    for dot_osu in BEATMAPS_DIRECTORY.iterdir():
        map_id = dot_osu.name[:-4]

        with dot_osu.open("r+") as osu:
            delimitation = osu.read(len(HTTP_459_RESPONSE))

            if "429 Too Many Requests" not in delimitation:
                continue

            corrupted += 1

            # prioritise osu.ppy.sh for beatmap, but if it fails, use mino.
            for host in mirror_order:
                if host.ratelimit_pause and host.ratelimit_pause > datetime.now():
                    continue

                if host.ratelimit_pause and host.ratelimit_pause < datetime.now():
                    print(f"{host.host}: ratelimited reset")
                    host.ratelimit_pause = None

                response = await client_session.get(host.endpoint.format(map_id=map_id))

                # if the response is 459, it should start ratelimit pause and use the next endpoint
                if response.status == 459:
                    host.ratelimit_pause = datetime.now() + timedelta(minutes=1, seconds=30)
                    print(
                        f"{host.host}: reached ratelimit and will continue to the other mirror."
                    )
                    continue

                # even if the map doesn't exist on bancho, it'll still return 200
                # therefore we need to check if the response text is empty.
                if host.host == "bancho" and response.status == 200:
                    decoded = await response.text()
                    if decoded == "":
                        print(
                            f"{host.host}: beatmap {map_id} doesn't exist on the official server, checking mirror."
                        )
                        continue

                if host.host == "mino":
                    # mino does handle it correctly and returns 404 if the beatmap doesn't exist.
                    # but we'll also want to check for other statuses.
                    if response.status != 200:
                        decoded = await response.json()
                        print(
                            f"{host.host}: beatmap {map_id} returned error: {decoded["error"]}"
                        )
                        continue

                    # use x-ratelimit-remaining to start ratelimit before 459 and save
                    # our ip from getting automatically banned.
                    ratelimit_remaining = response.headers["x-ratelimit-remaining"]

                    if ratelimit_remaining == 1:
                        host.ratelimit_pause = datetime.now() + timedelta(minutes=1, seconds=30)
                        continue

                if "nginx" in decoded:
                    print(f"{host.host}: unhandled response: (code {response.status})")
                    print(decoded)
                    continue

                # go back to the start
                osu.seek(0)
                # truncate all data
                osu.truncate()
                # write the new uncorrupted
                osu.write(decoded)
                # close file
                osu.close()

                host.corrected_files += 1
                print(f"{host.host}: corrected {dot_osu.name}.")

                await asyncio.sleep(0.5)
                break

    await client_session.close()

    print(
        "Finished looking through all saved .osu files",
        f"and fixed {MINO_OSU_ENDPOINT.corrected_files + BANCHO_OSU_ENDPOINT.corrected_files} files,",
        f"where Mino corrected {MINO_OSU_ENDPOINT.corrected_files} files and bancho corrected",
        f"{BANCHO_OSU_ENDPOINT.corrected_files} files",
    )

    return
