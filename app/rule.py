"""
Rule system for OpenManus.

This module provides functionality to load and apply rules to user prompts
before they are processed by the Manus agent.
"""

import os
from pathlib import Path
from typing import Optional
from loguru import logger

from app.config import config, PROJECT_ROOT


class RuleLoader:
    """
    Handles loading and processing of rule files for the Manus agent.
    
    The rule system allows users to define custom rules that are automatically
    prepended to user prompts when the rule system is activated.
    """
    
    def __init__(self):
        """Initialize the RuleLoader."""
        self._cached_rules: Optional[str] = None
        self._last_modified: Optional[float] = None
        
    def is_rule_system_enabled(self) -> bool:
        """
        Check if the rule system is enabled in configuration.
        
        Returns:
            True if rule system is enabled, False otherwise
        """
        try:
            return config.rule_config.activate if config.rule_config else False
        except Exception as e:
            logger.warning(f"Error checking rule system status: {e}")
            return False
    
    def get_rule_file_path(self) -> Path:
        """
        Get the absolute path to the rule file.
        
        Returns:
            Path object pointing to the rule file
            
        Raises:
            ValueError: If the rule path is not configured
        """
        if not config.rule_config or not config.rule_config.path:
            raise ValueError("Rule file path is not configured")
            
        rule_path = config.rule_config.path
        
        # Convert to Path object
        path = Path(rule_path)
        
        # If it's not absolute, make it relative to project root
        if not path.is_absolute():
            path = PROJECT_ROOT / path
            
        return path.resolve()
    
    def load_rules(self, force_reload: bool = False) -> Optional[str]:
        """
        Load rules from the configured rule file.
        
        Args:
            force_reload: If True, force reload even if cached version exists
            
        Returns:
            Rule content as string, or None if loading fails
        """
        if not self.is_rule_system_enabled():
            logger.debug("Rule system is disabled")
            return None
            
        try:
            rule_file_path = self.get_rule_file_path()
            
            # Check if file exists
            if not rule_file_path.exists():
                logger.warning(f"Rule file not found: {rule_file_path}")
                return None
                
            # Check if we need to reload
            current_modified = rule_file_path.stat().st_mtime
            if (not force_reload and 
                self._cached_rules is not None and 
                self._last_modified == current_modified):
                logger.debug("Using cached rules")
                return self._cached_rules
                
            # Load the file
            with rule_file_path.open('r', encoding='utf-8') as f:
                content = f.read().strip()
                
            if not content:
                logger.warning(f"Rule file is empty: {rule_file_path}")
                return None
                
            # Cache the content
            self._cached_rules = content
            self._last_modified = current_modified
            
            logger.info(f"Rules loaded from: {rule_file_path}")
            logger.debug(f"Rule content length: {len(content)} characters")
            
            return content
            
        except Exception as e:
            logger.error(f"Error loading rules: {e}")
            return None
    
    def apply_rules_to_prompt(self, user_prompt: str) -> str:
        """
        Apply rules to a user prompt by prepending rule content.
        
        Args:
            user_prompt: The original user prompt
            
        Returns:
            Modified prompt with rules prepended, or original prompt if no rules
        """
        if not user_prompt:
            return user_prompt
            
        rules = self.load_rules()
        if not rules:
            return user_prompt
            
        # Format the final prompt according to requirements
        formatted_prompt = f"{rules}\n\n以下是用户输入：\n{user_prompt}"
        
        logger.debug(f"Applied rules to prompt. Original length: {len(user_prompt)}, "
                    f"Final length: {len(formatted_prompt)}")
        
        return formatted_prompt
    
    def validate_rule_configuration(self) -> tuple[bool, str]:
        """
        Validate the current rule configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not config.rule_config:
                return True, "Rule configuration not set (optional)"
                
            if not config.rule_config.activate:
                return True, "Rule system is disabled"
                
            if not config.rule_config.path:
                return False, "Rule file path is not configured"
                
            rule_file_path = self.get_rule_file_path()
            
            if not rule_file_path.exists():
                return False, f"Rule file does not exist: {rule_file_path}"
                
            if not rule_file_path.is_file():
                return False, f"Rule path is not a file: {rule_file_path}"
                
            # Try to read the file
            try:
                with rule_file_path.open('r', encoding='utf-8') as f:
                    content = f.read()
                if not content.strip():
                    return False, f"Rule file is empty: {rule_file_path}"
            except Exception as e:
                return False, f"Cannot read rule file: {e}"
                
            return True, "Rule configuration is valid"
            
        except Exception as e:
            return False, f"Error validating rule configuration: {e}"
    
    def get_rule_info(self) -> dict:
        """
        Get information about the current rule configuration.
        
        Returns:
            Dictionary with rule system information
        """
        info = {
            "enabled": self.is_rule_system_enabled(),
            "configured": config.rule_config is not None,
            "path": None,
            "exists": False,
            "size": 0,
            "last_modified": None,
            "valid": False,
            "error": None
        }
        
        try:
            if config.rule_config and config.rule_config.path:
                rule_path = self.get_rule_file_path()
                info["path"] = str(rule_path)
                
                if rule_path.exists():
                    info["exists"] = True
                    stat = rule_path.stat()
                    info["size"] = stat.st_size
                    info["last_modified"] = stat.st_mtime
                    
            is_valid, error = self.validate_rule_configuration()
            info["valid"] = is_valid
            if not is_valid:
                info["error"] = error
                
        except Exception as e:
            info["error"] = str(e)
            
        return info


# Global instance
rule_loader = RuleLoader()


def apply_rules_to_prompt(user_prompt: str) -> str:
    """
    Convenience function to apply rules to a user prompt.
    
    Args:
        user_prompt: The original user prompt
        
    Returns:
        Modified prompt with rules applied
    """
    return rule_loader.apply_rules_to_prompt(user_prompt)


def is_rule_system_enabled() -> bool:
    """
    Convenience function to check if rule system is enabled.
    
    Returns:
        True if rule system is enabled
    """
    return rule_loader.is_rule_system_enabled()


def validate_rule_configuration() -> tuple[bool, str]:
    """
    Convenience function to validate rule configuration.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    return rule_loader.validate_rule_configuration()


def get_rule_info() -> dict:
    """
    Convenience function to get rule system information.
    
    Returns:
        Dictionary with rule system information
    """
    return rule_loader.get_rule_info()
