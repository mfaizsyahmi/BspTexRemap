
Class Console {
    static JOINER := "`n"
    , LOG_OFF := 0
    , LOG_ERROR := 1
    , LOG_WARN := 2
    , LOG_INFO := 3
    , LOG_VERBOSE := 4
	, LOG_BANNER := 0x10 ; unused atm
    , logMap := {0:0,1:1,2:2,3:3,4:4,off:0,error:1,warn:2,info:3,verbose:4}
    , logLevel := 1 ; current level. set before use

    static StdOut := FileOpen("*", "w")
    , StdErr := FileOpen("**", "w")

    _Log(level, messages*) {
        if (this.logLevel&0xF < level)
            return ; blackholes more verbose levels than required
        if (level == this.LOG_ERROR) {
            this.StdErr.WriteLine(Util.Array.Join(messages, this.JOINER))
			this.StdErr.Read(0) ; flush
		}
        else {
            this.StdOut.WriteLine(Util.Array.Join(messages, this.JOINER))
			this.StdOut.Read(0) ; flush
		}
    }
    Verbose(messages*) {
        this._Log(this.LOG_VERBOSE, messages*)
    }
    Info(messages*) {
        this._Log(this.LOG_INFO, messages*)
    }
    Warn(messages*) {
        this._Log(this.LOG_WARN, messages*)
    }
    Error(messages*) {
        this._Log(this.LOG_ERROR, messages*)
    }
	
	; the previous 4 methods but with F at end, with same effect as Format() 
    VerboseF(params*) {
        this._Log(this.LOG_VERBOSE, Format(params*))
    }
    InfoF(params*) {
        this._Log(this.LOG_INFO,Format(params*))
    }
    WarnF(params*) {
        this._Log(this.LOG_WARN, Format(params*))
    }
    ErrorF(params*) {
        this._Log(this.LOG_ERROR, Format(params*))
    }
	
    Banner() {
		this.StdOut.WriteLine(BANNER)
		this.StdOut.Read(0) ; flush
    }
    Help() {
		this.StdOut.WriteLine(ABOUT)
		this.StdOut.Read(0) ; flush
    }
}
