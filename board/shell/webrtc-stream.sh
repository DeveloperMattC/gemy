#!/bin/sh
# Browser-viewable WebRTC stream from the Coralboard (no monitor required).
#
#   webrtc-stream.sh start [test|cam]   # default: test pattern
#   webrtc-stream.sh stop
#   webrtc-stream.sh status
#
# Then open  http://<board-usb0-ip>:8080/  in a browser on the host PC,
# click the listed producer, and the live stream appears.

WEBDIR=/home/root/demos/webrtc
LOGDIR=/tmp/webrtc
HTTP_PORT=8090          # 8080 is taken by swupdate on this board
mkdir -p "$LOGDIR"

start_one() {            # name  logfile  command...
    name="$1"; log="$2"; shift 2
    nohup sh -c "exec $*" > "$LOGDIR/$log" 2>&1 &
    echo $! > "$LOGDIR/$name.pid"
}

stop() {
    for f in signal http producer; do
        if [ -f "$LOGDIR/$f.pid" ]; then
            kill "$(cat "$LOGDIR/$f.pid")" 2>/dev/null
            rm -f "$LOGDIR/$f.pid"
        fi
    done
    echo "Stopped."
}

status() {
    echo "Listening ports:"
    netstat -ltn 2>/dev/null | grep -E ":8443|:$HTTP_PORT" || echo "  (none yet)"
    echo "Producer log tail:"
    tail -n 6 "$LOGDIR/producer.log" 2>/dev/null
}

case "${1:-start}" in
  stop)   stop; exit 0 ;;
  status) status; exit 0 ;;
esac

SRC="${2:-test}"
stop >/dev/null 2>&1
sleep 1

# 1) signalling server  ws://0.0.0.0:8443
start_one signal signal.log "gst-webrtc-signalling-server"
sleep 1

# 2) static web server for the viewer page (8080 is used by swupdate, so 8090)
start_one http http.log "python3 -m http.server $HTTP_PORT --bind 0.0.0.0 --directory $WEBDIR"

# 3) producer pipeline -> webrtcsink (registers with the signalling server)
if [ "$SRC" = cam ]; then
    NAME=coralboard-camera
    PIPE='v4l2src device=/dev/video0 ! video/x-raw,width=1280,height=720 ! videoconvert ! webrtcsink meta="meta,name=coralboard-camera"'
else
    NAME=coralboard-test
    PIPE='videotestsrc is-live=true pattern=ball ! video/x-raw,width=1280,height=720,framerate=30/1 ! videoconvert ! webrtcsink meta="meta,name=coralboard-test"'
fi
start_one producer producer.log "gst-launch-1.0 -e $PIPE"

sleep 3
IP=$(ip addr show usb0 | sed -n 's/.*inet \([0-9.]*\).*/\1/p' | head -n 1)
echo "WebRTC stream started (source=$SRC, producer=$NAME)."
echo "Open in your host browser:  http://$IP:$HTTP_PORT/"
echo
status
