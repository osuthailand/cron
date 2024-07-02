from databases import Database
from redis import Redis
from app.constants import Gamemode, PlayMode
from app.objects.framework import Job, config


@config.register(name="recalculate_user_stats", is_controllable=True)
async def recalculate_user_stats(job: Job, database: Database, redis: Redis) -> None:
    """
    `recalculate_user_stats()` recalculates all users pp and accuracy
    for all play- and gamemodes.
    """
    print("Starting to recalculate all user stats")
    all_users = await database.fetch_all("SELECT * FROM users WHERE privileges & 4")

    for user in all_users:
        print(f"Recalculating {user["username"]}'s total weighted pp")

        for gamemode in Gamemode:
            for play_mode in PlayMode:
                if gamemode == Gamemode.RELAX and play_mode == PlayMode.MANIA:
                    continue

                important_scores = await database.fetch_all(
                    query="SELECT pp, accuracy FROM scores "
                    "WHERE user_id = :user_id AND mode = :mode "
                    "AND status = 3 AND gamemode = :gamemode "
                    "AND awards_pp = 1 ORDER BY pp DESC LIMIT 100",
                    values={
                        "user_id": user["id"],
                        "mode": play_mode.value,
                        "gamemode": gamemode.value,
                    },
                )

                if not important_scores:
                    print(
                        f"{user["username"]} hasn't submitted any scores on {gamemode.name.lower()} for {play_mode.name.lower()}.. ignore"
                    )
                    continue

                overall_accuracy = 0
                weighted_pp = 0

                for place, score in enumerate(important_scores):
                    overall_accuracy += score["accuracy"] * 0.95**place
                    weighted_pp += score["pp"] * 0.95**place

                # bonus accuracy
                overall_accuracy *= 100 / (20 * (1 - 0.95 ** len(important_scores)))
                overall_accuracy /= 100

                # bonus pp
                weighted_pp += 416.6667 * (1 - 0.9994 ** len(important_scores))

                await database.execute(
                    query=f"UPDATE {gamemode.table} SET {play_mode.to_db("pp")} = :new_pp, "
                    f"{play_mode.to_db("accuracy")} = :new_accuracy WHERE id = :user_id",
                    values={
                        "new_pp": weighted_pp,
                        "new_accuracy": overall_accuracy,
                        "user_id": user["id"],
                    },
                )

                # repopulate redis leaderboards
                await redis.zadd(
                    f"ragnarok:leaderboard:{gamemode.name.lower()}:{play_mode.value}",
                    {str(user["id"]): weighted_pp},
                )

                await redis.zadd(
                    f"ragnarok:leaderboard:{gamemode.name.lower()}:{user["country"]}:{play_mode.value}",
                    {str(user["id"]): weighted_pp},
                )

                print(f"Finished recalculating {user["username"]}'s pp and accuracy.")

    print("Finished recalculating all users weighted pp and overall accuracy.")
