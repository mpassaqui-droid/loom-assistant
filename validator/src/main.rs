// loom-validate: the real oracle for loom-assistant.
//
// Reads LOOM source on stdin, runs it through the actual loom-core parser and
// scheduler (never a simulation, never the LLM's own claim), and prints a JSON
// report of exactly what would play. loom-assistant's eval harness diffs this
// against the semantic intent of each golden-set prompt.
//
// loom-core::parse() never errors, even on garbage (confirmed empirically: it
// silently drops anything it doesn't recognize). So "did it parse" is not a
// meaningful signal on its own — the real signal is in `voices` and `events`
// below: an empty or unexpected result means the generation didn't do what was
// asked, even though the parser itself stayed silent about it.

use std::io::{self, Read};

fn wave_name(w: loom_core::Wave) -> &'static str {
    match w {
        loom_core::Wave::Sine => "sine",
        loom_core::Wave::Square => "square",
        loom_core::Wave::Saw => "saw",
        loom_core::Wave::Triangle => "triangle",
    }
}

fn main() {
    let mut src = String::new();
    io::stdin()
        .read_to_string(&mut src)
        .expect("failed to read LOOM source from stdin");

    let voices = loom_core::parse(&src);
    let key = loom_core::parse_key(&src);
    let bpm = loom_core::parse_bpm(&src);
    let seed = loom_core::parse_seed(&src);

    let events = loom_core::schedule_bar_seeded(&voices, key.as_ref(), 0, seed);

    let voices_json: Vec<serde_json::Value> = voices
        .iter()
        .map(|v| {
            serde_json::json!({
                "name": v.name,
                "tokens": v.tokens,
                "verbs": v.verbs,
                "is_drum": v.is_drum,
                "wave": wave_name(v.wave),
                "gain": v.gain,
            })
        })
        .collect();

    let events_json: Vec<serde_json::Value> = events
        .iter()
        .map(|e| {
            serde_json::json!({
                "phase": e.phase,
                "voice": e.voice,
                "token": e.token,
                "is_drum": e.is_drum,
                "freq": e.freq,
            })
        })
        .collect();

    let report = serde_json::json!({
        "bpm": if bpm > 0.0 { Some(bpm) } else { None },
        "voice_count": voices.len(),
        "event_count": events.len(),
        "voices": voices_json,
        "events": events_json,
    });

    println!("{}", report);
}
