"""
Chat Interface Component for GeoViz3D

This module contains the components for rendering the chat interface.
"""
import streamlit as st

def render_chat_interface():
    """
    Render the chat interface component.
    
    Returns:
        tuple: (user_input, location_input) - The text inputs from the user
    """
    st.subheader("📝 Ask me about places")
    
    # Display chat history
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Check if chat history exists and has items
    if hasattr(st.session_state, 'chat_history') and st.session_state.chat_history:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(
                    f'<div class="user-message">👤 <b>You:</b> {message["content"]}</div>', 
                    unsafe_allow_html=True
                )
            else:
                # Format the assistant's message
                formatted_content = format_assistant_message(message["content"])
                st.markdown(
                    f'<div class="bot-message">🌏 <b>GeoViz3D:</b> {formatted_content}</div>', 
                    unsafe_allow_html=True
                )
    else:
        st.markdown(
            '<div style="text-align: center; padding: 20px; color: #888;">Ask me anything about locations, maps, or geographical data!</div>', 
            unsafe_allow_html=True
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Input fields
    user_input = st.text_area(
        "What can I help you find or visualize?", 
        key="user_input", 
        placeholder="e.g., 'Show me all museums in Paris' or 'Find hospitals in Berlin'"
    )
    
    # Direct geocoding option
    location_input = st.text_input(
        "Or enter a location name to jump directly to it:", 
        key="location_input",
        placeholder="e.g., 'New York City' or 'Eiffel Tower, Paris'"
    )
    
    return user_input, location_input

def format_assistant_message(content):
    """
    Format the assistant's message content.
    
    This function handles any special formatting needed for the assistant's messages,
    such as highlighting code blocks, handling overpass queries, etc.
    
    Args:
        content (str): The raw message content
        
    Returns:
        str: The formatted message content
    """
    # Remove the overpass code block from the display
    # We'll still extract and use it, but we don't need to show the raw query to the user
    if "```overpass" in content and "```" in content.split("```overpass")[1]:
        # Extract parts before and after the code block
        parts = content.split("```overpass")
        before = parts[0]
        after = parts[1].split("```", 1)[1] if "```" in parts[1] else ""
        return before + after
    
    # Handle regular code blocks
    elif "```" in content:
        # Replace code blocks with styled code blocks
        parts = content.split("```")
        formatted_parts = []
        
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Not a code block
                formatted_parts.append(part)
            else:  # Code block
                language = part.split("\n")[0] if "\n" in part else ""
                code = part[len(language):].strip() if language else part
                formatted_parts.append(f'<div style="background-color: #f8f8f8; padding: 10px; border-radius: 5px; font-family: monospace;">{code}</div>')
        
        return "".join(formatted_parts)
    
    # Default: return the content as is
    return content

def clear_chat_history():
    """Clear the chat history."""
    st.session_state.chat_history = []