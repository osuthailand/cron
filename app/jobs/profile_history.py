from datetime import datetime, timedelta
from databases import Database
from redis import Redis
from app.constants import Gamemode, PlayMode
from app.objects.framework import Job, JobStatus, config


@config.register(name="fill_profile_history", interval=60)  # every minute
async def fill_profile_history(job: Job, database: Database, redis: Redis) -> None:
    # ensure stats recalculation isn't already in progress
    recalc_job = config.jobs["recalculate_user_stats"]

    if recalc_job.status == JobStatus.IN_PROGRESS:
        return

    # small hack for it to run on each day shift.
    current_date = datetime.now().date()
    latest_date = await database.fetch_val(
        "SELECT timestamp FROM profile_history ORDER BY timestamp DESC LIMIT 1"
    )

    if current_date == latest_date:
        return

    print("Logging all active (played the last 3 months) players history")
    all_unrestricted_users = await database.fetch_all(
        "SELECT id, username FROM users WHERE privileges & 4 "
        "AND latest_activity_time >= :active_time AND id > 1 ",
        {"active_time": (datetime.now() - timedelta(weeks=12)).timestamp()},
    )

    for user in all_unrestricted_users:
        print(f"Logging {user["username"]}'s ({user["id"]}) profile history")

        for gamemode in Gamemode:
            for play_mode in PlayMode:
                if gamemode == Gamemode.RELAX and play_mode == PlayMode.MANIA:
                    continue

                current_pp = await database.fetch_val(
                    f"SELECT CAST({play_mode.to_db("pp")} AS INT) AS pp "
                    f"FROM {gamemode.table} WHERE id = :user_id",
                    {"user_id": user["id"]},
                )

                if current_pp == 0:
                    # no pp, don't matter
                    continue

                _current_rank = await redis.zrevrank(
                    f"ragnarok:leaderboard:{gamemode.name.lower()}:{play_mode}",
                    str(user["id"]),
                )
                current_rank = _current_rank + 1 if _current_rank is not None else 0

                await database.execute(
                    "INSERT INTO profile_history (user_id, pp, rank, gamemode, mode) "
                    "VALUES (:user_id, :pp, :rank, :gamemode, :mode)",
                    {
                        "user_id": user["id"],
                        "pp": current_pp,
                        "rank": current_rank,
                        "gamemode": gamemode,
                        "mode": play_mode,
                    },
                )

        print(f"successfully logged {user["username"]}'s history for today.")
