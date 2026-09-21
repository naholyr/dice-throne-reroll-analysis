def symbol_config(distribution: str) -> dict[str, object]:
    return {
        "distribution": distribution,
        **{
            identifier: {"color": "#ffffff", "name": f"Symbole {identifier}"}
            for identifier in dict.fromkeys(distribution)
        },
    }
