"""LLM Prompt 定义"""


def get_system_prompt(config=None):
    """获取系统提示词
    
    Args:
        config: 业务配置实例，如果为 None 则使用默认的 business_config
    """
    from config.business_config import business_config
    if config:
        return config.get_llm_system_prompt()
    return business_config.get_llm_system_prompt()
