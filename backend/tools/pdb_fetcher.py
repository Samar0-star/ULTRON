import os
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

def fetch_pdb(pdb_id: str, dest_dir: str = "data") -> str:
    """
    Autonomously fetch a PDB file from RCSB.
    Returns the absolute path to the downloaded file.
    """
    pdb_id = pdb_id.lower().strip()
    if len(pdb_id) != 4:
        raise ValueError(f"Invalid PDB ID: {pdb_id}")
    
    os.makedirs(dest_dir, exist_ok=True)
    file_path = os.path.join(dest_dir, f"{pdb_id}.pdb")
    
    if os.path.exists(file_path):
        logger.info(f" [PDB] {pdb_id} already exists at {file_path}")
        return os.path.abspath(file_path)
        
    url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
    logger.info(f" [PDB] Fetching {pdb_id} from RCSB...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(file_path, "w") as f:
            f.write(response.text)
        logger.info(f" [PDB] Successfully downloaded {pdb_id} to {file_path}")
        return os.path.abspath(file_path)
    except Exception as e:
        logger.error(f" [PDB] Failed to fetch {pdb_id}: {e}")
        raise ValueError(f"Failed to fetch PDB {pdb_id}: {e}")

def get_pdb_fetcher():
    def fetch_pdb_tool(pdb_id: str) -> str:
        """Fetch a PDB file from RCSB given a 4-character PDB ID (e.g., '6m0j')"""
        return fetch_pdb(pdb_id)
    return fetch_pdb_tool
