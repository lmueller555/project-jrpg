"""Deterministic, bounded rising aether shared by map and battle exports."""
import math

PERIOD_MS=12000
COLORS=((166,219,235),(194,235,244),(129,182,233),(188,161,221),(151,213,180),(232,197,151))

def strands(bounds,elapsed_ms,reduced_motion=False):
    x,y,w,h=bounds
    time=0. if reduced_motion else (elapsed_ms%PERIOD_MS)/PERIOD_MS
    result=[]
    for i in range(11):
        phase=i*.381966
        life=(time+phase)%1
        root_x=x+w*(.17+.66*((i*7%11)/10))
        root_y=y+h*(.47+.22*((i*3%7)/6))
        height=h*(.48+.22*(i%3)/2)
        points=[]
        for j in range(20):
            f=j/19
            dx=math.sin(f*5+phase*math.tau+time*math.tau)*w*.025+math.sin(f*9+phase)*w*.012
            points.append((round(root_x+dx+f*f*w*.035*math.sin(phase*9)),round(root_y-f*height)))
        # The moving highlight travels up each thread; the thread never pops in.
        segments=[]
        for j in range(19):
            f=j/19
            envelope=math.sin(math.pi*max(.02,min(.98,f)))**.7
            distance=abs(f-life)
            alpha=round(envelope*(30+145*max(0,1-distance/.22)))
            segments.append((points[j],points[j+1],COLORS[i%len(COLORS)],alpha))
        result.extend(segments)
    return result

def draw_aether(target,camera,bounds,elapsed_ms,reduced_motion=False):
    import pygame
    x,y,w,h=bounds
    viewport=pygame.Rect(round(camera[0]),round(camera[1]),*target.get_size())
    if not viewport.colliderect(pygame.Rect(x,y-h,w,h*2)):return
    layer=pygame.Surface(target.get_size(),pygame.SRCALPHA)
    # A quiet below-floor glow never erases the dark centre of the pit.
    pulse=.65 if reduced_motion else .55+.10*math.cos(elapsed_ms/PERIOD_MS*math.tau)
    glow=pygame.Rect(round(x-camera[0]+w*.08),round(y-camera[1]+h*.32),round(w*.84),round(h*.43))
    pygame.draw.ellipse(layer,(58,104,134,round(15*pulse)),glow)
    for a,b,color,alpha in strands(bounds,elapsed_ms,reduced_motion):
        a=(a[0]-camera[0],a[1]-camera[1]);b=(b[0]-camera[0],b[1]-camera[1])
        pygame.draw.line(layer,(*color,alpha//5),a,b,3)
        pygame.draw.line(layer,(*color,alpha),a,b,1)
    target.blit(layer,(0,0))
