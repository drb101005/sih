-- ====================================================================
-- Railway Maintenance Optimizer: Supabase Database Schema Migration
-- ====================================================================

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- --------------------------------------------------------------------
-- 1. CORRIDORS TABLE (First-Class Corridor Management)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS corridors (
    corridor_id VARCHAR(32) PRIMARY KEY,
    corridor_name VARCHAR(255) NOT NULL,
    zone VARCHAR(64) DEFAULT 'Indian Railways',
    division VARCHAR(64) DEFAULT 'General Division',
    
    start_station VARCHAR(128) NOT NULL,
    end_station VARCHAR(128) NOT NULL,
    start_chainage_km NUMERIC(8, 2) DEFAULT 0.00,
    end_chainage_km NUMERIC(8, 2) NOT NULL,
    
    track_type VARCHAR(32) DEFAULT 'DOUBLE', -- 'SINGLE', 'DOUBLE', 'MULTIPLE'
    electrification_type VARCHAR(32) DEFAULT '25KV_AC', -- '25KV_AC', 'DIESEL', 'HYBRID'
    traffic_density_class VARCHAR(16) DEFAULT 'HIGH', -- 'HIGH', 'MEDIUM', 'LOW'
    
    status VARCHAR(32) DEFAULT 'OPERATIONAL', -- 'OPERATIONAL', 'SPEED_RESTRICTION', 'MAINTENANCE_BLOCKED', 'CLOSED'
    speed_restriction_kmph INT DEFAULT NULL,
    notes TEXT DEFAULT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_corridors_status ON corridors(status);
CREATE INDEX IF NOT EXISTS idx_corridors_zone ON corridors(zone);

-- --------------------------------------------------------------------
-- 2. TASKS TABLE (Maintenance Requests / Work Orders)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    task_id VARCHAR(64) PRIMARY KEY,
    asset_id VARCHAR(64),
    asset_type VARCHAR(128),
    corridor_id VARCHAR(32) REFERENCES corridors(corridor_id) ON DELETE SET NULL,
    location VARCHAR(128),
    chainage_km NUMERIC(8, 2) NOT NULL,
    department VARCHAR(64) NOT NULL, -- 'Engineering', 'Signal', 'Traction'
    task_type VARCHAR(128) NOT NULL,
    maintenance_type VARCHAR(64) DEFAULT 'Corrective',
    
    defect_id VARCHAR(64) DEFAULT 'NONE',
    defect_information TEXT DEFAULT 'NONE',
    defect_severity VARCHAR(32) DEFAULT 'NONE', -- 'NONE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    asset_criticality VARCHAR(32) DEFAULT 'MEDIUM',
    safety_impact VARCHAR(32) DEFAULT 'MEDIUM',
    operational_impact VARCHAR(32) DEFAULT 'MEDIUM',
    
    probability_of_failure NUMERIC(6, 4) DEFAULT NULL, -- Calculated by ML risk model
    due_date DATE,
    estimated_duration_minutes INT NOT NULL,
    required_resources TEXT NOT NULL, -- Semicolon-separated e.g. 'Signal_Team_08;Machine_A'
    required_isolation VARCHAR(64) DEFAULT 'NONE', -- 'NONE', 'TRACK', 'OHE', 'SIGNAL', 'ALL'
    
    allowed_start_time TIME DEFAULT '00:00:00',
    allowed_end_time TIME DEFAULT '00:00:00',
    overdue_days NUMERIC(6, 2) DEFAULT 0.0,
    
    priority_score NUMERIC(6, 4) DEFAULT NULL,
    priority_class VARCHAR(16) DEFAULT NULL, -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    
    status VARCHAR(32) DEFAULT 'PENDING', -- 'PENDING', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_corridor ON tasks(corridor_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_chainage ON tasks(corridor_id, chainage_km);

-- --------------------------------------------------------------------
-- 3. BLOCKS TABLE (Corridor Traffic & Maintenance Windows)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS blocks (
    block_id VARCHAR(64) PRIMARY KEY,
    corridor_id VARCHAR(32) REFERENCES corridors(corridor_id) ON DELETE CASCADE,
    location VARCHAR(128),
    station VARCHAR(128),
    chainage_from_km NUMERIC(8, 2) NOT NULL,
    chainage_to_km NUMERIC(8, 2) NOT NULL,
    
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INT NOT NULL,
    block_type VARCHAR(64) DEFAULT 'CORRIDOR_BLOCK',
    availability VARCHAR(32) DEFAULT 'AVAILABLE', -- 'AVAILABLE', 'PROVISIONAL', 'COMMITTED', 'CANCELLED'
    
    restrictions TEXT,
    affected_infrastructure TEXT,
    isolation_required VARCHAR(64) DEFAULT 'NONE',
    allowed_departments TEXT DEFAULT 'Engineering;Signal;Traction',
    max_resources INT DEFAULT 5,
    
    operational_cost NUMERIC(10, 2) DEFAULT 0.0,
    traffic_level VARCHAR(32) DEFAULT 'MEDIUM',
    goods_impact_score NUMERIC(10, 4) DEFAULT 0.0,
    expected_goods_trains INT DEFAULT 0,
    conflicting_trains NUMERIC(6, 2) DEFAULT 0.0,
    conflict_severity NUMERIC(6, 2) DEFAULT 0.0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_blocks_corridor ON blocks(corridor_id);
CREATE INDEX IF NOT EXISTS idx_blocks_availability ON blocks(availability);
CREATE INDEX IF NOT EXISTS idx_blocks_timerange ON blocks(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_blocks_chainage ON blocks(corridor_id, chainage_from_km, chainage_to_km);

-- --------------------------------------------------------------------
-- 4. SCHEDULES TABLE (Committed / Optimized Schedule Output)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(64) REFERENCES tasks(task_id) ON DELETE CASCADE,
    block_id VARCHAR(64) REFERENCES blocks(block_id) ON DELETE CASCADE,
    corridor_id VARCHAR(32) REFERENCES corridors(corridor_id) ON DELETE SET NULL,
    
    scheduled_start TIMESTAMP WITH TIME ZONE NOT NULL,
    scheduled_end TIMESTAMP WITH TIME ZONE NOT NULL,
    estimated_duration_minutes INT NOT NULL,
    required_resources TEXT,
    resource_count INT DEFAULT 1,
    max_resources INT DEFAULT 5,
    
    priority_score NUMERIC(6, 4),
    priority_class VARCHAR(16),
    final_score NUMERIC(8, 6),
    
    duration_fit NUMERIC(6, 4),
    cost_score NUMERIC(6, 4),
    goods_score NUMERIC(6, 4),
    train_conflict_score NUMERIC(6, 4),
    resource_score NUMERIC(6, 4),
    
    explanation_facts JSONB DEFAULT '{}'::jsonb,
    schedule_status VARCHAR(32) DEFAULT 'SCHEDULED', -- 'SCHEDULED', 'CONFIRMED', 'CANCELLED', 'EXECUTED'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_task_schedule UNIQUE (task_id, block_id, scheduled_start)
);

CREATE INDEX IF NOT EXISTS idx_schedules_task ON schedules(task_id);
CREATE INDEX IF NOT EXISTS idx_schedules_block ON schedules(block_id);
CREATE INDEX IF NOT EXISTS idx_schedules_corridor ON schedules(corridor_id);
CREATE INDEX IF NOT EXISTS idx_schedules_time ON schedules(scheduled_start, scheduled_end);

-- --------------------------------------------------------------------
-- 5. AUTO-UPDATE TIMESTAMP TRIGGER FUNCTION
-- --------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS trg_corridors_updated_at ON corridors;
CREATE TRIGGER trg_corridors_updated_at BEFORE UPDATE ON corridors FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_tasks_updated_at ON tasks;
CREATE TRIGGER trg_tasks_updated_at BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_blocks_updated_at ON blocks;
CREATE TRIGGER trg_blocks_updated_at BEFORE UPDATE ON blocks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_schedules_updated_at ON schedules;
CREATE TRIGGER trg_schedules_updated_at BEFORE UPDATE ON schedules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
