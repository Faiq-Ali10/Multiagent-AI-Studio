def voice_over_parser_prompt(input_text: str, previous: str = None) -> str:
    if not previous:
        return f"""
        You are an expert casting director for a video production studio.
        
        Extract the script and voice profile from the user request.
        
        Return your answer in strictly valid JSON format with exactly five keys using these EXACT domains:
        * "transcript": The exact words to be spoken.
        * "gender": Choose ONLY from ["Male", "Female"].
        * "speed": The rate adjustment. Domain: a string from ["-50%", "-25%", "+0%", "+25%", "+50%"].
        * "pitch": The vocal frequency. Domain: a string from ["-20Hz", "-10Hz", "+0Hz", "+10Hz", "+20Hz"].
        * "voice_type": The locale and personality style. Choose ONLY from:
            ["en-US-AriaNeural", "en-US-ChristopherNeural", "en-GB-SoniaNeural", "en-GB-RyanNeural", "ar-EG-SalmaNeural", "ar-SA-HamedNeural", "en-AU-NatashaNeural", "en-IN-NeerjaNeural"].
        
        CRITICAL RULES:
        1. Output ONLY raw JSON. No markdown, no intro.
        2. Start with {{ and end with }}.
        3. If the user asks for a "sweet" or "happy" tone, use "AriaNeural" (Female) or "ChristopherNeural" (Male).
        
        EXAMPLE:
        User Request: "Make a fast male voice say hello in a British accent"
        Output:
        {{
            "transcript": "hello",
            "gender": "Male",
            "speed": "+25%",
            "pitch": "+0Hz",
            "voice_type": "en-GB-RyanNeural"
        }}
        
        USER REQUEST: 
        "{input_text}"
        """
    else:
        return f"""
        You are an expert casting director. Analyze the new request against the previous context.
        
        LOGIC:
        1. If the new request is a script edit (e.g., "add word Faiq"), update "transcript" but KEEP all other settings from the previous profile.
        2. If the new request is a setting change (e.g., "make it slower"), update only that setting.
        3. If it is a new request, ignore previous context.
        
        Return your answer in strictly valid JSON format with these domains:
        * "transcript": The full updated script.
        * "gender": ["Male", "Female"].
        * "speed": ["-50%", "-25%", "+0%", "+25%", "+50%"].
        * "pitch": ["-20Hz", "-10Hz", "+0Hz", "+10Hz", "+20Hz"].
        * "voice_type": ["en-US-AriaNeural", "en-US-ChristopherNeural", "en-GB-SoniaNeural", "en-GB-RyanNeural", "ar-EG-SalmaNeural", "ar-SA-HamedNeural", "en-AU-NatashaNeural", "en-IN-NeerjaNeural"].

        CRITICAL RULES:
        1. Output ONLY raw JSON.
        2. Inherit ALL settings from PREVIOUS PROFILE unless explicitly told to change them.

        EXAMPLES:
        
        Example 1 (Script Edit):
        Previous: Script: "I love you" | Profile: {{'gender': 'Male', 'speed': '+0%', 'pitch': '-10Hz', 'voice_type': 'en-US-ChristopherNeural'}}
        New Request: "add word Faiq"
        Output:
        {{
            "transcript": "I love you Faiq",
            "gender": "Male",
            "speed": "+0%",
            "pitch": "-10Hz",
            "voice_type": "en-US-ChristopherNeural"
        }}
        
        Example 2 (Setting Edit):
        Previous: Script: "Hello" | Profile: {{'gender': 'Female', 'speed': '+0%', 'pitch': '+0Hz', 'voice_type': 'en-US-AriaNeural'}}
        New Request: "make it very slow"
        Output:
        {{
            "transcript": "Hello",
            "gender": "Female",
            "speed": "-50%",
            "pitch": "+0Hz",
            "voice_type": "en-US-AriaNeural"
        }}
        
        PREVIOUS CONTEXT: 
        "{previous}"
        
        NEW REQUEST: 
        "{input_text}"
        """
