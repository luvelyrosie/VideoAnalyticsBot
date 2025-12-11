CREATE TABLE videos (
    id TEXT PRIMARY KEY,
    creator_id TEXT NOT NULL,
    video_created_at TIMESTAMPTZ NOT NULL,
    views_count INTEGER NOT NULL DEFAULT 0,
    likes_count INTEGER NOT NULL DEFAULT 0,
    comments_count INTEGER NOT NULL DEFAULT 0,
    reports_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE video_snapshots (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    views_count INTEGER NOT NULL DEFAULT 0,
    likes_count INTEGER NOT NULL DEFAULT 0,
    comments_count INTEGER NOT NULL DEFAULT 0,
    reports_count INTEGER NOT NULL DEFAULT 0,
    delta_views_count INTEGER NOT NULL DEFAULT 0,
    delta_likes_count INTEGER NOT NULL DEFAULT 0,
    delta_comments_count INTEGER NOT NULL DEFAULT 0,
    delta_reports_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_videos_creator_id ON videos(creator_id);
CREATE INDEX idx_videos_created_at ON videos(video_created_at);
CREATE INDEX idx_snapshots_video_id ON video_snapshots(video_id);
CREATE INDEX idx_snapshots_created_at ON video_snapshots(created_at);