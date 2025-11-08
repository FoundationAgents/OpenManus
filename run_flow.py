import asyncio
import time

from app.agent.data_analysis import DataAnalysis
from app.agent.manus import Manus
from app.config import config
from app.flow.flow_factory import FlowFactory, FlowType
from app.flow.ade_flow import ADEFlow
from app.logger import logger
from app.mcp.bridge import MCPBridge


async def run_flow():
    bridge = MCPBridge()
    
    try:
        # Initialize MCP bridge
        await bridge.initialize()
        logger.info(f"MCP Bridge initialized (fallback: {bridge.is_fallback_active()})")
        
        prompt = input("Enter your prompt: ")

        if prompt.strip().isspace() or not prompt:
            logger.warning("Empty prompt provided.")
            return

        # Determine which flow to use based on configuration and prompt complexity
        mode = config.run_flow_config.default_mode
        
        # Check if ADE mode should be used for complex tasks
        if config.run_flow_config.enable_ade_mode and _is_complex_task(prompt):
            mode = "ade"
            
        logger.warning(f"Processing your request using {mode} flow...")

        try:
            start_time = time.time()
            
            if mode == "ade":
                result = await run_ade_flow(prompt, bridge)
            else:
                result = await run_planning_flow(prompt, bridge)
                
            elapsed_time = time.time() - start_time
            logger.info(f"Request processed in {elapsed_time:.2f} seconds")
            logger.info(result)
            
        except asyncio.TimeoutError:
            logger.error("Request processing timed out after 1 hour")
            logger.info(
                "Operation terminated due to timeout. Please try a simpler request."
            )

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        await bridge.cleanup()


def _is_complex_task(prompt: str) -> bool:
    """Determine if a task is complex enough to require ADE mode."""
    complexity_indicators = [
        "system", "architecture", "design", "implement", "build", "create",
        "application", "software", "project", "multiple", "several", "various",
        "integrate", "deploy", "test", "debug", "refactor", "optimize"
    ]
    
    prompt_lower = prompt.lower()
    
    # Check for complexity indicators
    indicator_count = sum(1 for indicator in complexity_indicators if indicator in prompt_lower)
    
    # Check for length (longer prompts are often more complex)
    length_score = min(len(prompt.split()) / 50, 2)  # Normalize to max 2 points
    
    # Total complexity score
    complexity_score = indicator_count + length_score
    
    return complexity_score >= 3  # Threshold for ADE mode


async def run_ade_flow(prompt: str, bridge: MCPBridge) -> str:
    """Run the ADE (Agentic Development Environment) flow."""
    logger.info("Initializing ADE flow for complex task")
    
    # Check if multi-agent mode is enabled
    if config.run_flow_config.enable_multi_agent:
        return await run_enhanced_multi_agent_flow(prompt, bridge)
    
    # Create agents for ADE
    from app.agent.swe_agent import SWEAgent
    
    agents = {
        "swe": SWEAgent(),
    }
    
    # Add data analysis agent if configured
    if config.run_flow_config.use_data_analysis_agent:
        agents["data_analysis"] = DataAnalysis()
    
    # Create ADE flow with bridge
    ade_flow = ADEFlow(agents=agents, bridge=bridge)
    
    result = await asyncio.wait_for(
        ade_flow.execute(prompt),
        timeout=3600,  # 60 minute timeout
    )
    
    return result


async def run_enhanced_multi_agent_flow(prompt: str, bridge: MCPBridge) -> str:
    """Run the enhanced multi-agent flow."""
    logger.info("Initializing Enhanced Multi-Agent Environment")
    
    from app.flow.enhanced_async_flow import EnhancedAsyncFlow
    from app.agent.manus import Manus
    
    # Create enhanced flow with multi-agent environment
    agents = {}
    
    # Add base agents
    agents["manus"] = await Manus.create()
    
    # Add data analysis agent if configured
    if config.run_flow_config.use_data_analysis_agent:
        agents["data_analysis"] = DataAnalysis()
    
    # Create enhanced async flow with bridge
    enhanced_flow = EnhancedAsyncFlow(agents=agents, bridge=bridge)
    
    result = await asyncio.wait_for(
        enhanced_flow.execute(prompt),
        timeout=7200,  # 120 minute timeout for multi-agent coordination
    )
    
    return result


async def run_planning_flow(prompt: str, bridge: MCPBridge) -> str:
    """Run the standard planning flow."""
    logger.info("Initializing planning flow")
    
    agents = {
        "manus": Manus(),
    }
    
    if config.run_flow_config.use_data_analysis_agent:
        agents["data_analysis"] = DataAnalysis()
        
    flow = FlowFactory.create_flow(
        flow_type=FlowType.PLANNING,
        agents=agents,
        bridge=bridge,
    )
    
    result = await asyncio.wait_for(
        flow.execute(prompt),
        timeout=3600,  # 60 minute timeout
    )
    
    return result


if __name__ == "__main__":
    asyncio.run(run_flow())
