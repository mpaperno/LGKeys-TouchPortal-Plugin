-- [LGKeys start] integration script
function OnEvent(event, arg, family)
	-- uncomment below to see output messages in the LGS scrpting console
	--OutputLogMessage("event = %s, arg = %s, family = %s\n", event, arg, family)
	DbgHook(event, arg, family)
end

function DbgHook(event, arg, family)
	if (event == "PROFILE_ACTIVATED") then
		arg = "PROFILE_NAME"
	end
	-- the format of this message should not be changed
	OutputDebugMessage("%s.%s.%s", event, family, arg)
end
-- [LGKeys end] integration script
