"""Inject professional knowledge into GBT brain at startup"""
import sys, os

def inject_knowledge():
    """Patch brain with A-Share + Desktop expertise"""
    try:
        from gbt.knowledge import SYSTEM_KNOWLEDGE
        from gbt.brain import AutonomousBrain
        
        # Monkey-patch: append knowledge to brain's get_context
        original_get_context = AutonomousBrain.get_context
        
        def enhanced_context(self):
            ctx = original_get_context(self)
            ctx += "\n\n[Professional Knowledge Base]\n" + SYSTEM_KNOWLEDGE
            return ctx
        
        AutonomousBrain.get_context = enhanced_context
        
        # Also patch system prompt if accessible
        try:
            from gbt import message as msg
            if hasattr(msg, 'SYSTEM_PROMPT'):
                msg.SYSTEM_PROMPT = msg.SYSTEM_PROMPT + "\n" + SYSTEM_KNOWLEDGE
            if hasattr(msg, 'DEFAULT_SYSTEM'):
                msg.DEFAULT_SYSTEM = msg.DEFAULT_SYSTEM + "\n" + SYSTEM_KNOWLEDGE
        except:
            pass
            
        print("[KNOWLEDGE] A-Share + Desktop expertise injected")
        return True
    except Exception as e:
        print(f"[KNOWLEDGE] Injection failed: {e}")
        return False
