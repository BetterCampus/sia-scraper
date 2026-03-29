"""Oracle ADF XML Event Payloads.

This module defines XML payloads for Oracle ADF RichClient events.
These payloads are sent in HTTP requests to trigger component behaviors.
"""

DROPDOWN_EVENT_VALUE: str = '<m xmlns="http://oracle.com/richClient/comm"><k v="autoSubmit"><b>1</b></k><k v="suppressMessageShow"><s>true</s></k><k v="type"><s>valueChange</s></k></m>'

BTTN_EVENT_VALUE: str = (
    '<m xmlns="http://oracle.com/richClient/comm"><k v="type"><s>action</s></k></m>'
)

SELECT_ROW_EVENT_VALUE: str = (
    '<m xmlns="http://oracle.com/richClient/comm"><k v="type"><s>selection</s></k></m>'
)

SESSION_TIMEOUT_ALERT: str = "AdfPage.PAGE.__getSessionTimeoutHelper().__alertTimeout()"
