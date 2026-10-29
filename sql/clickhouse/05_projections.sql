ALTER TABLE raw.events
    ADD PROJECTION IF NOT EXISTS p_by_listing
    (
        SELECT event_time, event_type, user_id, listing_id, platform, is_promoted
        ORDER BY listing_id, event_time
    );

ALTER TABLE raw.events MATERIALIZE PROJECTION p_by_listing SETTINGS mutations_sync = 2;
