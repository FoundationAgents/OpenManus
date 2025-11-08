"""
Backup Scheduler
Handles automatic backup scheduling
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.logger import logger
from app.config import config
from .backup_service import BackupService, BackupConfig


class BackupScheduler:
    """Schedules automatic backups"""
    
    def __init__(self):
        self.backup_service = BackupService()
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
        self._schedules: Dict[str, BackupConfig] = {}
        self._setup_default_schedules()
    
    def _setup_default_schedules(self):
        """Setup default backup schedules"""
        if config.backup.enable_backups:
            # Daily full backup
            self._schedules["daily_full"] = BackupConfig(
                backup_name="daily_full",
                backup_type="full",
                include_workspace=config.backup.include_workspace,
                include_config=config.backup.include_config,
                include_database=config.backup.include_database,
                compression=config.backup.compression,
                encryption=config.backup.encryption,
                locations=config.backup.backup_locations
            )
            
            # Weekly differential backup
            self._schedules["weekly_diff"] = BackupConfig(
                backup_name="weekly_differential",
                backup_type="differential",
                include_workspace=config.backup.include_workspace,
                include_config=config.backup.include_config,
                include_database=config.backup.include_database,
                compression=config.backup.compression,
                encryption=config.backup.encryption,
                locations=config.backup.backup_locations
            )
    
    async def start(self):
        """Start the backup scheduler"""
        if not config.backup.enable_backups:
            logger.info("Backup scheduler disabled in configuration")
            return
        
        logger.info("Starting backup scheduler...")
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Backup scheduler started")
    
    async def stop(self):
        """Stop the backup scheduler"""
        logger.info("Stopping backup scheduler...")
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Backup scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self._running:
            try:
                await self._check_and_run_scheduled_backups()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in backup scheduler loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _check_and_run_scheduled_backups(self):
        """Check if any scheduled backups need to run"""
        now = datetime.now()
        
        # Check daily backup (runs at 2 AM)
        if now.hour == 2 and now.minute == 0:
            if "daily_full" in self._schedules:
                await self._run_scheduled_backup("daily_full")
        
        # Check weekly backup (runs on Sunday at 3 AM)
        if now.weekday() == 6 and now.hour == 3 and now.minute == 0:  # Sunday = 6
            if "weekly_diff" in self._schedules:
                await self._run_scheduled_backup("weekly_diff")
    
    async def _run_scheduled_backup(self, schedule_name: str):
        """Run a scheduled backup"""
        try:
            if schedule_name not in self._schedules:
                logger.warning(f"Unknown backup schedule: {schedule_name}")
                return
            
            backup_config = self._schedules[schedule_name]
            logger.info(f"Running scheduled backup: {schedule_name}")
            
            result = await self.backup_service.create_backup(backup_config)
            
            if result.success:
                logger.info(f"Scheduled backup completed: {result.file_path}")
                
                # Clean up old backups after successful backup
                await self.backup_service.cleanup_old_backups()
            else:
                logger.error(f"Scheduled backup failed: {result.error_message}")
                
        except Exception as e:
            logger.error(f"Error running scheduled backup {schedule_name}: {e}")
    
    def add_schedule(self, name: str, backup_config: BackupConfig):
        """Add a new backup schedule"""
        self._schedules[name] = backup_config
        logger.info(f"Added backup schedule: {name}")
    
    def remove_schedule(self, name: str) -> bool:
        """Remove a backup schedule"""
        if name in self._schedules:
            del self._schedules[name]
            logger.info(f"Removed backup schedule: {name}")
            return True
        return False
    
    def list_schedules(self) -> Dict[str, BackupConfig]:
        """List all backup schedules"""
        return self._schedules.copy()
    
    async def run_backup_now(self, schedule_name: str) -> bool:
        """Run a backup immediately"""
        try:
            if schedule_name not in self._schedules:
                logger.error(f"Unknown backup schedule: {schedule_name}")
                return False
            
            await self._run_scheduled_backup(schedule_name)
            return True
            
        except Exception as e:
            logger.error(f"Error running backup {schedule_name}: {e}")
            return False
    
    async def get_next_run_time(self, schedule_name: str) -> Optional[datetime]:
        """Get the next run time for a schedule"""
        now = datetime.now()
        
        if schedule_name == "daily_full":
            # Next 2 AM
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        
        elif schedule_name == "weekly_diff":
            # Next Sunday at 3 AM
            days_until_sunday = (6 - now.weekday()) % 7
            next_run = now + timedelta(days=days_until_sunday)
            next_run = next_run.replace(hour=3, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(weeks=1)
            return next_run
        
        return None


# Global backup scheduler instance
backup_scheduler = BackupScheduler()
