#!/usr/bin/env python3
"""
Production Scheduler for LinkedIn Outreach Automation

Runs batch processing on a schedule (daily, weekly, etc.)
Can be used with cron or systemd timers.

Usage:
    # Run daily at 9 AM
    python3 scheduler.py --schedule daily --time "09:00"
    
    # Run weekly on Mondays at 10 AM
    python3 scheduler.py --schedule weekly --day monday --time "10:00"
    
    # Run immediately (for testing)
    python3 scheduler.py --run-now
"""

import os
import sys
import time
import argparse
import schedule
import logging
from datetime import datetime
from pathlib import Path
import json

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'scheduler_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def run_batch(profiles_file: str, send_messages: bool = True):
    """Run batch processing."""
    from batch_processor import BatchProcessor
    
    logger.info(f"Starting batch processing from {profiles_file}")
    
    processor = BatchProcessor(
        delay_between_profiles=30,
        delay_between_messages=60
    )
    
    # Load profiles
    profiles = processor.load_profiles_from_file(profiles_file)
    
    if not profiles:
        logger.error(f"No profiles found in {profiles_file}")
        return False
    
    # Process batch
    result = processor.process_batch(
        profiles,
        send_messages=send_messages
    )
    
    # Save results
    results_file = log_dir / f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Batch processing complete. Results saved to {results_file}")
    logger.info(f"Processed: {result['processed']}, Succeeded: {result['succeeded']}, Failed: {result['failed']}")
    
    return result['succeeded'] > 0


def main():
    parser = argparse.ArgumentParser(description="Schedule LinkedIn outreach batch processing")
    parser.add_argument('--profiles-file', default='profiles_batch.txt', help='Path to profiles file')
    parser.add_argument('--schedule', choices=['daily', 'weekly', 'hourly'], help='Schedule type')
    parser.add_argument('--time', help='Time to run (HH:MM format)')
    parser.add_argument('--day', choices=['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'], help='Day of week (for weekly schedule)')
    parser.add_argument('--run-now', action='store_true', help='Run immediately instead of scheduling')
    parser.add_argument('--no-send', action='store_true', help='Skip sending messages')
    
    args = parser.parse_args()
    
    if args.run_now:
        logger.info("Running batch immediately...")
        success = run_batch(args.profiles_file, send_messages=not args.no_send)
        sys.exit(0 if success else 1)
    
    if not args.schedule:
        logger.error("Must specify --schedule or --run-now")
        parser.print_help()
        sys.exit(1)
    
    # Setup schedule
    if args.schedule == 'daily':
        if not args.time:
            logger.error("--time required for daily schedule")
            sys.exit(1)
        schedule.every().day.at(args.time).do(run_batch, args.profiles_file, not args.no_send)
        logger.info(f"Scheduled daily run at {args.time}")
    
    elif args.schedule == 'weekly':
        if not args.day or not args.time:
            logger.error("--day and --time required for weekly schedule")
            sys.exit(1)
        day_map = {
            'monday': schedule.every().monday,
            'tuesday': schedule.every().tuesday,
            'wednesday': schedule.every().wednesday,
            'thursday': schedule.every().thursday,
            'friday': schedule.every().friday,
            'saturday': schedule.every().saturday,
            'sunday': schedule.every().sunday
        }
        day_map[args.day].at(args.time).do(run_batch, args.profiles_file, not args.no_send)
        logger.info(f"Scheduled weekly run on {args.day} at {args.time}")
    
    elif args.schedule == 'hourly':
        schedule.every().hour.do(run_batch, args.profiles_file, not args.no_send)
        logger.info("Scheduled hourly runs")
    
    # Run scheduler loop
    logger.info("Scheduler started. Waiting for scheduled jobs...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()

