#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# Markov/tools/async_utils.py

import asyncio
import logging


async def graceful_async_shutdown(ib=None):
    """
    Clean asyncio shutdown:
    - disconnect IBKR
    - cancel remaining asyncio tasks
    """

    try:
        # 1️⃣ IB sauber trennen
        if ib is not None:
            try:
                if ib.client.isConnected():
                    await ib.disconnect()
            except Exception as e:
                logging.debug(f"IB disconnect warning: {e}")

        # 2️⃣ alle übrigen asyncio Tasks canceln
        pending = [
            t for t in asyncio.all_tasks()
            if t is not asyncio.current_task()
        ]

        for t in pending:
            t.cancel()

        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    except Exception as e:
        logging.debug(f"Async shutdown cleanup warning: {e}")

