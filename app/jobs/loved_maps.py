from databases import Database
from redis import Redis
from app.objects.framework import Job, config

@config.register("ensure_loved_maps_dont_award_pp", interval=3600) # every hour
async def ensure_loved_maps_dont_award_pp(job: Job, database: Database, redis: Redis) -> None:
    """
    `ensure_loved_maps_dont_award_pp()` ensures that all scores, that
    has been submitted on a loved beatmap, doesn't have the awards_pp field
    set to true
    """
    print("Started fixing all pp-awarded loved scores")
    all_awarded_loved_scores = await database.fetch_all(
        "SELECT s.id FROM scores s INNER JOIN beatmaps b ON b.map_md5 = s.map_md5 "
        "WHERE b.approved = 5 AND s.awards_pp = 1"
    )

    if not all_awarded_loved_scores:
        print("No loved scores has awarded pp.")
        return

    for score in all_awarded_loved_scores:
        await database.execute("UPDATE scores SET awards_pp = 0 WHERE id = :id", {"id": score["id"]})
        print(f"Updated {score["id"]} to not award pp, as it was submitted on a loved map")

    print(f"Fixed {len(all_awarded_loved_scores)} scores awarding pp on a loved")
