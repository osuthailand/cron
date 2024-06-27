from databases import Database
from redis import Redis
from app.objects.framework import Job, config


@config.register(name="repopulate_redis_cache", interval=300)  # every 5 minutes
async def repopulate_redis_cache(job: Job, database: Database, redis: Redis) -> None:
    """
    `repopulate_redis_cache()` repopulates all server stats cached in redis.
    This includes total scores and accumulated pp across all gamemodes
    and playmodes.
    """

    print("starting to repopulate redis cache")
    total_scores = await database.fetch_val("SELECT COUNT(*) FROM scores")

    if not total_scores:
        print("failed to fetch scores?")
    else:
        await redis.set("ragnarok:total_scores", total_scores)
        print("populated ragnarok:total_scores")

    accumulated_pp = await database.fetch_val(
        "SELECT SUM(pp) FROM scores WHERE awards_pp = 1"
    )

    if not accumulated_pp:
        print("failed to fetch pp?")
    else:
        await redis.set("ragnarok:total_pp", accumulated_pp)
        print("populated ragnarok:total_pp")

    print("finished repopulating redis cache")
