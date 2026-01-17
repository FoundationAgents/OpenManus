"""
OpenManus Configurator
"""

def main():
    lines = ["[llm]"]

    def get_or_default(prompt, default):
        value = input(prompt + " (" + default + "): ").strip()
        return value if value else default

    print("__________________________________________________________")
    print("OpenManus Configuration")
    print("__________________________________________________________")
    print("")
    print("Please enter the following information to configure OpenManus")
    print("")
    print("")
    lines.append(
        f"api_type = \"{get_or_default('API Type, openai or azure', 'openai')}\""
    )
    # Azure needs a version too
    if lines[-1] == "azure":
        lines.append(
            f"api_version = \"{get_or_default('API Version', '2024-08-01-preview')}\""
        )
    lines.append(f"model = \"{get_or_default('Model', 'claude-3-5-sonnet')}\"")
    lines.append(
        f"base_url = \"{get_or_default('Base URL', 'https://api.openai.com/v1')}\""
    )
    lines.append(f"api_key = \"{get_or_default('API Key',"sk-...")}\"")
    lines.append(f"max_tokens = {get_or_default('Max Tokens', '4096')}")
    lines.append(f"temperature = {get_or_default('Temperature', '0.0')}")

    if input("Do you want to configure a vision model? Y/n (n)") == "Y":
        lines.append("")
        lines.append("[llm.vision]")
        lines.append(
            f"api_type = \"{get_or_default('API Type, openai or azure', 'openai')}\""
        )
        # Azure needs a version too
        if lines[-1] == "azure":
            lines.append(
                f"api_version = \"{get_or_default('API Version', '2024-08-01-preview')}\""
            )
        lines.append(f"model = \"{get_or_default('Model', 'claude-3-5-sonnet')}\"")
        lines.append(
            f"base_url = \"{get_or_default('Base URL', 'https://api.openai.com/v1')}\""
        )
        lines.append(f"api_key = \"{get_or_default('API Key',"sk-...")}\"")
        lines.append(f"max_tokens = {get_or_default('Max Tokens', '4096')}")
        lines.append(f"temperature = {get_or_default('Temperature', '0.0')}")

    with open("config/config.toml", "w", encoding="utf-8") as file:
        file.writelines("\n".join(lines))


if __name__ == "__main__":
    main()
