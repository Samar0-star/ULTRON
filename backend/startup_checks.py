"""
SVEL AI Scientist Startup Checks
Run this script to validate backend health before starting the server.
"""
import sys
import os
import logging
import importlib
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.llm_manager import LLMManager
from backend.memory.memory_manager import get_memory_manager

logger = logging.getLogger("startup_checks")

def check_llm():
    logger.info("Checking LLM Manager...")
    try:
        llm = LLMManager()
        health = llm.health()
        logger.info(f"LLM Health: {health}")
        if health["status"] not in ["ok", "degraded"]:
            return False
        logger.info(" LLM Manager responsive")
        return True
    except Exception as e:
        logger.error(f"LLM Manager check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_memory():
    logger.info("Checking Memory Manager...")
    try:
        mem = get_memory_manager()
        health = mem.health()
        logger.info(f"Memory Health: {health}")
        if health["status"] != "ok":
            logger.warning(f"Memory Manager degraded: {health}")
        logger.info(" Memory Manager responsive")
        return True
    except Exception as e:
        logger.error(f"Memory Manager check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    logger.info("="*60)
    logger.info("Starting Avon-1 Startup Checks...")
    logger.info("="*60)
    
    llm_ok = check_llm()
    mem_ok = check_memory()
    
    logger.info("=" *60)
    if llm_ok and mem_ok:
        logger.info(" ALL SYSTEMS RESPONSIVE")
        logger.info("="*60)
        sys.exit(0)
    else:
        logger.error(" SOME SYSTEM CHECKS FAILED")
        logger.info("="*60)
        sys.exit(1)

if __name__ == "__main__":
    main()
