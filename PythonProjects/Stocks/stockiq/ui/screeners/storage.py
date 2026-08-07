"""
Screener Storage

Persists and retrieves saved screeners for reuse.
"""

import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from .criteria import (
    CompositeFilter,
    FilterCondition,
    FilterOperator,
    ComparisonOperator,
    get_criteria_by_name,
)


class ScreenerStorage:
    """
    Manages persistent storage of saved screeners.
    
    Screeners are stored as JSON files in a designated directory.
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize screener storage.
        
        Args:
            storage_dir: Directory for storing screener files.
                        Defaults to ~/.stockiq/screeners/
        """
        if storage_dir is None:
            storage_dir = os.path.join(
                os.path.expanduser("~"),
                ".stockiq",
                "screeners"
            )
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def save(
        self,
        screener: CompositeFilter,
        overwrite: bool = False
    ) -> str:
        """
        Save a screener to storage.
        
        Args:
            screener: CompositeFilter to save
            overwrite: Whether to overwrite existing screener with same name
        
        Returns:
            Path to saved file
        
        Raises:
            ValueError: If screener has no name or file already exists
        """
        if not screener.name:
            raise ValueError("Screener must have a name to be saved")
        
        # Sanitize filename
        filename = self._sanitize_filename(screener.name) + ".json"
        filepath = self.storage_dir / filename
        
        # Check if exists
        if filepath.exists() and not overwrite:
            raise ValueError(
                f"Screener '{screener.name}' already exists. "
                "Use overwrite=True to replace."
            )
        
        # Serialize to JSON
        screener_dict = self._serialize_screener(screener)
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(screener_dict, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def load(self, name: str) -> CompositeFilter:
        """
        Load a screener from storage.
        
        Args:
            name: Name of the screener to load
        
        Returns:
            Loaded CompositeFilter
        
        Raises:
            FileNotFoundError: If screener not found
        """
        filename = self._sanitize_filename(name) + ".json"
        filepath = self.storage_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Screener '{name}' not found")
        
        # Read from file
        with open(filepath, 'r', encoding='utf-8') as f:
            screener_dict = json.load(f)
        
        # Deserialize
        return self._deserialize_screener(screener_dict)
    
    def delete(self, name: str) -> bool:
        """
        Delete a screener from storage.
        
        Args:
            name: Name of the screener to delete
        
        Returns:
            True if deleted, False if not found
        """
        filename = self._sanitize_filename(name) + ".json"
        filepath = self.storage_dir / filename
        
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    
    def list_screeners(self) -> List[Dict[str, Any]]:
        """
        List all saved screeners.
        
        Returns:
            List of dictionaries with screener metadata
        """
        screeners = []
        
        for filepath in self.storage_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    screener_dict = json.load(f)
                
                screeners.append({
                    'name': screener_dict.get('name'),
                    'description': screener_dict.get('description'),
                    'created_at': screener_dict.get('created_at'),
                    'modified_at': screener_dict.get('modified_at'),
                    'condition_count': len(screener_dict.get('conditions', [])),
                    'operator': screener_dict.get('operator'),
                })
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️  Warning: Could not load {filepath.name}: {e}")
                continue
        
        return sorted(screeners, key=lambda x: x.get('modified_at', ''), reverse=True)
    
    def exists(self, name: str) -> bool:
        """Check if a screener exists"""
        filename = self._sanitize_filename(name) + ".json"
        filepath = self.storage_dir / filename
        return filepath.exists()
    
    def _serialize_screener(self, screener: CompositeFilter) -> Dict[str, Any]:
        """Serialize CompositeFilter to dictionary"""
        return {
            'name': screener.name,
            'description': screener.description,
            'operator': screener.operator.value,
            'conditions': [
                {
                    'criteria_name': condition.criteria.name,
                    'operator': condition.operator.value,
                    'value': condition.value,
                    'negate': condition.negate,
                }
                for condition in screener.conditions
            ],
            'created_at': datetime.now().isoformat(),
            'modified_at': datetime.now().isoformat(),
            'version': '1.0',
        }
    
    def _deserialize_screener(self, data: Dict[str, Any]) -> CompositeFilter:
        """Deserialize dictionary to CompositeFilter"""
        conditions = []
        
        for cond_dict in data.get('conditions', []):
            criteria = get_criteria_by_name(cond_dict['criteria_name'])
            if criteria is None:
                print(f"⚠️  Warning: Unknown criteria '{cond_dict['criteria_name']}', skipping")
                continue
            
            condition = FilterCondition(
                criteria=criteria,
                operator=ComparisonOperator(cond_dict['operator']),
                value=cond_dict['value'],
                negate=cond_dict.get('negate', False),
            )
            conditions.append(condition)
        
        return CompositeFilter(
            conditions=conditions,
            operator=FilterOperator(data.get('operator', 'AND')),
            name=data.get('name'),
            description=data.get('description'),
        )
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize screener name for use as filename"""
        # Replace invalid characters with underscores
        invalid_chars = '<>:"/\\|?*'
        sanitized = name
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        
        return sanitized.strip()
    
    def export_screener(self, name: str, output_path: str) -> None:
        """
        Export a screener to a specific file path.
        
        Args:
            name: Name of the screener to export
            output_path: Destination file path
        """
        screener = self.load(name)
        screener_dict = self._serialize_screener(screener)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(screener_dict, f, indent=2, ensure_ascii=False)
    
    def import_screener(
        self,
        input_path: str,
        new_name: Optional[str] = None,
        overwrite: bool = False
    ) -> str:
        """
        Import a screener from a file.
        
        Args:
            input_path: Source file path
            new_name: Optional new name for imported screener
            overwrite: Whether to overwrite existing screener
        
        Returns:
            Name of imported screener
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            screener_dict = json.load(f)
        
        screener = self._deserialize_screener(screener_dict)
        
        if new_name:
            screener.name = new_name
        
        self.save(screener, overwrite=overwrite)
        
        return screener.name
